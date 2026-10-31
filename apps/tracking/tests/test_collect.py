"""
The collector, the drain, identification and pruning.

The collector is the project's first unauthenticated high-write path and it is
open to every plan including Free, so the shape that matters is: it never fails
loudly, it never writes in the request, and it cannot be used to learn or
assert who a contact is.
"""
import json
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.accounts.models import Organization, User
from apps.contacts.models import Contact
from apps.tracking import services
from apps.tracking.models import TrackedEvent, Visitor


class CollectorTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.url = reverse('tracking:collect')
        cache.clear()
        self.addCleanup(cache.clear)
        self._clear_buffer()
        self.addCleanup(self._clear_buffer)

    def _clear_buffer(self):
        client = services._redis()
        if client is not None:
            client.delete(services.BUFFER_KEY)
        else:
            cache.delete(services.BUFFER_KEY)

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload),
            content_type='text/plain;charset=UTF-8',
        )

    def _view(self, path='/pricing', **over):
        return {
            't': 'pageview', 'u': f'https://acme.test{path}', 'p': path,
            'ti': 'Pricing', 'r': 'https://google.com',
            'at': timezone.now().isoformat(), **over,
        }

    def _collect(self, visitor='v-1', events=None, key=None):
        response = self._post({
            'k': str(key or self.org.tracking_key),
            'vid': visitor,
            'e': events if events is not None else [self._view()],
        })
        services.drain_buffer()
        return response


class CollectEndpointTests(CollectorTestCase):
    def test_a_page_view_is_recorded(self):
        response = self._collect()

        self.assertEqual(response.status_code, 204)
        event = TrackedEvent.objects.get()
        self.assertEqual(event.path, '/pricing')
        self.assertEqual(event.organization, self.org)
        self.assertEqual(event.visitor.visitor_id, 'v-1')

    def test_nothing_is_written_during_the_request(self):
        """The request buffers and returns; a beat task does the writing."""
        self._post({
            'k': str(self.org.tracking_key), 'vid': 'v-1', 'e': [self._view()],
        })
        self.assertEqual(TrackedEvent.objects.count(), 0)

        services.drain_buffer()
        self.assertEqual(TrackedEvent.objects.count(), 1)

    def test_every_outcome_is_204(self):
        """
        A visitor's browser can do nothing with an error, and a 429 only tells
        an abuser that their flood is working.
        """
        for payload in (
            {},
            {'k': 'nonsense', 'vid': 'v', 'e': []},
            {'k': str(self.org.tracking_key), 'vid': '', 'e': [self._view()]},
            {'k': str(self.org.tracking_key), 'vid': 'v', 'e': 'not-a-list'},
        ):
            self.assertEqual(self._post(payload).status_code, 204, payload)

    def test_malformed_json_does_not_raise(self):
        response = self.client.post(
            self.url, data='{not json', content_type='text/plain',
        )
        self.assertEqual(response.status_code, 204)

    def test_an_unknown_key_writes_nothing(self):
        self._collect(key='00000000-0000-0000-0000-000000000000')
        self.assertEqual(TrackedEvent.objects.count(), 0)

    def test_an_oversized_body_is_dropped_before_parsing(self):
        response = self.client.post(
            self.url, data='x' * (services.MAX_BODY_BYTES + 1),
            content_type='text/plain',
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(TrackedEvent.objects.count(), 0)

    def test_a_batch_is_capped(self):
        self._collect(events=[self._view(f'/p{i}') for i in range(50)])
        self.assertEqual(
            TrackedEvent.objects.count(), services.MAX_EVENTS_PER_REQUEST
        )

    def test_long_values_are_truncated_not_rejected(self):
        """Losing the event entirely is worse than losing the tail of a title."""
        self._collect(events=[self._view(ti='T' * 400)])

        event = TrackedEvent.objects.get()
        self.assertEqual(len(event.title), 255)

    def test_counters_move_with_the_visitor(self):
        self._collect(events=[self._view('/a'), self._view('/b')])

        visitor = Visitor.objects.get()
        self.assertEqual(visitor.page_view_count, 2)

    def test_one_organizations_key_cannot_write_into_another(self):
        other = Organization.objects.create(name='Other', slug='other')
        self._collect(key=other.tracking_key)

        self.assertEqual(
            TrackedEvent.objects.filter(organization=self.org).count(), 0
        )
        self.assertEqual(
            TrackedEvent.objects.filter(organization=other).count(), 1
        )


class IdentifyTests(CollectorTestCase):
    def setUp(self):
        super().setUp()
        self.contact = Contact.objects.create(
            organization=self.org, email='ada@example.com',
        )

    def test_earlier_visits_are_backfilled_onto_the_contact(self):
        self._collect(events=[self._view('/pricing'), self._view('/cases')])
        self.assertEqual(
            TrackedEvent.objects.filter(contact__isnull=True).count(), 2
        )

        services.identify(self.org, 'v-1', self.contact)

        self.assertEqual(
            TrackedEvent.objects.filter(contact=self.contact).count(), 2
        )
        self.assertIsNotNone(Visitor.objects.get().identified_at)

    def test_later_visits_arrive_already_attributed(self):
        services.identify(self.org, 'v-1', self.contact)
        self._collect(events=[self._view('/after')])

        self.assertEqual(TrackedEvent.objects.get().contact, self.contact)

    def test_a_visitor_is_not_relinked_to_a_second_contact(self):
        """
        A shared browser. Keeping the first identification beats letting the
        second rewrite the first person's history.
        """
        other = Contact.objects.create(
            organization=self.org, email='bob@example.com',
        )
        services.identify(self.org, 'v-1', self.contact)
        services.identify(self.org, 'v-1', other)

        self.assertEqual(Visitor.objects.get().contact, self.contact)

    def test_backfill_does_not_reach_past_the_window(self):
        self._collect(events=[self._view('/old')])
        TrackedEvent.objects.update(
            occurred_at=timezone.now() - timedelta(days=services.BACKFILL_DAYS + 5)
        )

        services.identify(self.org, 'v-1', self.contact)

        self.assertEqual(
            TrackedEvent.objects.filter(contact=self.contact).count(), 0
        )

    def test_there_is_no_endpoint_that_takes_an_email(self):
        """
        One would answer "does this address have an account here", and would
        let anyone attach an invented history to a real person -- which feeds
        lead scores and segments, and therefore sends. Identification happens
        server-side, from a form submission that already resolved the contact.
        """
        for name in ('tracking:identify', 'tracking:associate'):
            with self.assertRaises(NoReverseMatch):
                reverse(name)


class PruneTests(CollectorTestCase):
    @override_settings(TRACKING_RETENTION_DAYS=30)
    def test_old_anonymous_visitors_and_events_are_deleted(self):
        from apps.tracking.tasks import prune_tracked_events

        self._collect(events=[self._view('/old')])
        old = timezone.now() - timedelta(days=45)
        TrackedEvent.objects.update(occurred_at=old)
        Visitor.objects.update(last_seen_at=old)

        prune_tracked_events()

        self.assertEqual(TrackedEvent.objects.count(), 0)
        self.assertEqual(Visitor.objects.count(), 0)

    @override_settings(TRACKING_RETENTION_DAYS=30)
    def test_an_identified_visitor_survives(self):
        """Once a visitor is a contact, their history is CRM data."""
        from apps.tracking.tasks import prune_tracked_events

        contact = Contact.objects.create(
            organization=self.org, email='ada@example.com',
        )
        self._collect(events=[self._view('/old')])
        services.identify(self.org, 'v-1', contact)
        Visitor.objects.update(last_seen_at=timezone.now() - timedelta(days=45))

        prune_tracked_events()

        self.assertEqual(Visitor.objects.count(), 1)


class ThrottleTests(CollectorTestCase):
    def test_a_flood_from_one_site_is_dropped(self):
        from apps.tracking import throttle

        original = throttle.PER_SITE_PER_MINUTE
        throttle.PER_SITE_PER_MINUTE = 3
        self.addCleanup(setattr, throttle, 'PER_SITE_PER_MINUTE', original)

        for _ in range(8):
            self._post({
                'k': str(self.org.tracking_key), 'vid': 'v-1',
                'e': [self._view()],
            })
        services.drain_buffer()

        # Dropped, not refused: the response is the same 204 either way.
        self.assertLessEqual(TrackedEvent.objects.count(), 3)


class SubmissionIdentifiesVisitorTests(CollectorTestCase):
    """
    The whole identification path, which is deliberately the only one.

    A browser sends an opaque visitor id with its form submission; the server
    resolves the contact from the submitted email and links the two. The email
    never travels between frames and no endpoint ever accepts one alongside a
    visitor id.
    """

    def test_submitting_a_form_attaches_the_visitors_earlier_pages(self):
        from apps.forms.models import Form, FormField

        form = Form.objects.create(
            organization=self.org, name='Newsletter', status='active',
            form_type='popup',
        )
        email_field = FormField.objects.create(
            form=form, label='Email', field_type='email', is_required=True,
            contact_field_mapping='email', order=0,
        )

        self._collect(events=[self._view('/pricing'), self._view('/cases')])

        response = self.client.post(
            f'/api/v1/public/forms/{form.id}/submit/',
            {
                'data': {str(email_field.id): 'ada@example.com'},
                'visitor_id': 'v-1',
                'source_url': 'https://acme.test/pricing',
            },
            format='json',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201, response.content[:300])
        contact = Contact.objects.get(email='ada@example.com')
        self.assertEqual(
            TrackedEvent.objects.filter(contact=contact).count(), 2,
            'the two pages read before converting',
        )
        self.assertEqual(Visitor.objects.get().contact, contact)

    def test_a_submission_without_a_visitor_id_still_works(self):
        """Tracking is optional; lead capture is not."""
        from apps.forms.models import Form, FormField

        form = Form.objects.create(
            organization=self.org, name='Inline', status='active',
        )
        email_field = FormField.objects.create(
            form=form, label='Email', field_type='email', is_required=True,
            contact_field_mapping='email', order=0,
        )

        response = self.client.post(
            f'/api/v1/public/forms/{form.id}/submit/',
            {'data': {str(email_field.id): 'bob@example.com'}},
            format='json', content_type='application/json',
        )

        self.assertEqual(response.status_code, 201, response.content[:300])
        self.assertTrue(Contact.objects.filter(email='bob@example.com').exists())
