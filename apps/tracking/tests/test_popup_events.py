"""
Measuring a pop-up, and the targeting the browser cannot decide alone.

The numbers these produce are the ones a marketer uses to keep or kill a
pop-up, so the cases worth pinning are the ones where a count could be wrong:
events for a pop-up the key does not own, a conversion counted twice, and a
rate computed from an impression count of zero.
"""
import json
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Organization, User
from apps.contacts.models import Contact
from apps.forms.models import Form, FormField
from apps.popups.models import Popup
from apps.popups.services import PopupAnalyticsService
from apps.tracking import services
from apps.tracking.models import TrackedEvent


class PopupEventTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.popup = Popup.objects.create(
            organization=self.org, name='Newsletter', cta_text='Subscribe',
            status=Popup.STATUS_PUBLISHED,
        )
        self.url = reverse('tracking:collect')
        cache.clear()
        self.addCleanup(cache.clear)
        cache.delete(services.BUFFER_KEY)

    def _send(self, event_type, popup_id=None, visitor='v-1'):
        self.client.post(
            self.url,
            data=json.dumps({
                'k': str(self.org.tracking_key),
                'vid': visitor,
                'e': [{
                    't': event_type,
                    'pu': str(popup_id or self.popup.id),
                    'u': 'https://acme.test/pricing',
                    'p': '/pricing',
                    'at': timezone.now().isoformat(),
                }],
            }),
            content_type='text/plain;charset=UTF-8',
        )
        services.drain_buffer()


class ImpressionTests(PopupEventTestCase):
    def test_a_shown_event_is_recorded_against_the_popup(self):
        self._send('popup_shown')

        event = TrackedEvent.objects.get()
        self.assertEqual(event.event_type, 'popup_shown')
        self.assertEqual(event.popup, self.popup)

    def test_the_cached_counter_moves(self):
        self._send('popup_shown')
        self._send('popup_shown', visitor='v-2')
        self._send('popup_clicked')

        self.popup.refresh_from_db()
        self.assertEqual(self.popup.impression_count, 2)
        self.assertEqual(self.popup.click_count, 1)

    def test_a_dismissal_is_recorded_but_counts_toward_nothing(self):
        """It is a rate, not a counter: dismissals are read from the events."""
        self._send('popup_dismissed')

        self.popup.refresh_from_db()
        self.assertEqual(self.popup.impression_count, 0)
        self.assertEqual(
            TrackedEvent.objects.filter(event_type='popup_dismissed').count(), 1
        )

    def test_an_event_for_another_accounts_popup_is_dropped(self):
        """A hand-edited id must not inflate someone else's numbers."""
        other = Organization.objects.create(name='Other', slug='other')
        theirs = Popup.objects.create(
            organization=other, name='Theirs', cta_text='Go',
        )

        self._send('popup_shown', popup_id=theirs.id)

        self.assertEqual(TrackedEvent.objects.count(), 0)
        theirs.refresh_from_db()
        self.assertEqual(theirs.impression_count, 0)

    def test_a_page_view_carries_no_popup(self):
        self.client.post(
            self.url,
            data=json.dumps({
                'k': str(self.org.tracking_key), 'vid': 'v-1',
                'e': [{'t': 'pageview', 'p': '/pricing',
                       'at': timezone.now().isoformat()}],
            }),
            content_type='text/plain',
        )
        services.drain_buffer()

        self.assertIsNone(TrackedEvent.objects.get().popup_id)


class ConversionTests(PopupEventTestCase):
    def test_submitting_the_embedded_form_credits_the_popup(self):
        form = Form.objects.create(
            organization=self.org, name='Signup', status='active',
        )
        field = FormField.objects.create(
            form=form, label='Email', field_type='email', is_required=True,
            contact_field_mapping='email', order=0,
        )
        self.popup.form = form
        self.popup.save(update_fields=['form'])

        response = self.client.post(
            f'/api/v1/public/forms/{form.id}/submit/',
            data=json.dumps({
                'data': {str(field.id): 'ada@example.com'},
                'popup_id': str(self.popup.id),
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201, response.content[:200])
        self.popup.refresh_from_db()
        self.assertEqual(self.popup.conversion_count, 1)

    def test_a_popup_id_from_another_account_credits_nothing(self):
        other = Organization.objects.create(name='Other', slug='other')
        theirs = Popup.objects.create(
            organization=other, name='Theirs', cta_text='Go',
        )
        form = Form.objects.create(
            organization=self.org, name='Signup', status='active',
        )
        field = FormField.objects.create(
            form=form, label='Email', field_type='email', is_required=True,
            contact_field_mapping='email', order=0,
        )

        self.client.post(
            f'/api/v1/public/forms/{form.id}/submit/',
            data=json.dumps({
                'data': {str(field.id): 'ada@example.com'},
                'popup_id': str(theirs.id),
            }),
            content_type='application/json',
        )

        theirs.refresh_from_db()
        self.assertEqual(theirs.conversion_count, 0)


class AnalyticsTests(PopupEventTestCase):
    def test_rates_are_computed_from_the_events(self):
        for visitor in ('a', 'b', 'c', 'd'):
            self._send('popup_shown', visitor=visitor)
        self._send('popup_clicked', visitor='a')
        self._send('popup_dismissed', visitor='b')

        stats = PopupAnalyticsService.get_popup_analytics(self.popup, days=30)

        self.assertEqual(stats['impressions'], 4)
        self.assertEqual(stats['unique_views'], 4)
        self.assertEqual(stats['clicks'], 1)
        self.assertEqual(stats['dismissals'], 1)
        # No form, so a click is the conversion.
        self.assertEqual(stats['conversions'], 1)
        self.assertEqual(stats['conversion_rate'], 25.0)
        self.assertEqual(stats['dismiss_rate'], 25.0)

    def test_a_popup_nobody_has_seen_reads_zero_not_an_error(self):
        stats = PopupAnalyticsService.get_popup_analytics(self.popup, days=30)

        self.assertEqual(stats['impressions'], 0)
        self.assertEqual(stats['conversion_rate'], 0.0)

    def test_repeat_views_by_one_visitor_are_impressions_but_one_unique(self):
        self._send('popup_shown')
        self._send('popup_shown')

        stats = PopupAnalyticsService.get_popup_analytics(self.popup, days=30)

        self.assertEqual(stats['impressions'], 2)
        self.assertEqual(stats['unique_views'], 1)

    def test_events_outside_the_window_are_excluded(self):
        self._send('popup_shown')
        TrackedEvent.objects.update(
            occurred_at=timezone.now() - timedelta(days=90)
        )

        stats = PopupAnalyticsService.get_popup_analytics(self.popup, days=30)

        self.assertEqual(stats['impressions'], 0)


class AudienceTests(PopupEventTestCase):
    def setUp(self):
        super().setUp()
        self.url_audience = reverse('tracking:audience')

    def _ask(self, visitor='v-1'):
        response = self.client.post(
            self.url_audience,
            data=json.dumps({'k': str(self.org.tracking_key), 'vid': visitor}),
            content_type='text/plain',
        )
        return response

    def test_nothing_is_asked_when_no_popup_targets_an_audience(self):
        """An organization that targets nothing exposes nothing."""
        response = self._ask()

        body = response.json()
        self.assertEqual(body['segments'], {})
        self.assertEqual(body['tags'], {})
        self.assertFalse(body['known'])

    def test_an_unidentified_visitor_is_not_known(self):
        from apps.contacts.models import Tag

        tag = Tag.objects.create(organization=self.org, name='VIP')
        self.popup.targeting = {'audience': {'tags': [str(tag.id)]}}
        self.popup.save(update_fields=['targeting'])

        self.assertFalse(self._ask().json()['known'])

    def test_an_identified_visitor_is_answered_in_booleans(self):
        from apps.contacts.models import ContactTag, Tag

        tag = Tag.objects.create(organization=self.org, name='VIP')
        other_tag = Tag.objects.create(organization=self.org, name='Cold')
        contact = Contact.objects.create(
            organization=self.org, email='ada@example.com',
        )
        ContactTag.objects.create(contact=contact, tag=tag)
        services.identify(self.org, 'v-1', contact)

        self.popup.targeting = {
            'audience': {'tags': [str(tag.id), str(other_tag.id)]}
        }
        self.popup.save(update_fields=['targeting'])

        body = self._ask().json()

        self.assertTrue(body['known'])
        self.assertTrue(body['tags'][str(tag.id)])
        self.assertFalse(body['tags'][str(other_tag.id)])
        # Booleans only -- never the list of what they belong to.
        self.assertNotIn('tag_names', body)

    def test_the_response_is_never_cached_by_anything_in_between(self):
        self.assertEqual(self._ask()['Cache-Control'], 'no-store')

    def test_an_unknown_key_is_answered_with_nothing(self):
        response = self.client.post(
            self.url_audience,
            data=json.dumps({'k': '00000000-0000-0000-0000-000000000000',
                             'vid': 'v-1'}),
            content_type='text/plain',
        )
        self.assertEqual(response.json(), {})

    def test_location_is_none_without_a_geo_database(self):
        """
        An unknown country must fail a location rule rather than pass it:
        an Ireland-only offer shown to the world is worse than one nobody
        sees.
        """
        self.assertIsNone(self._ask().json().get('country'))
