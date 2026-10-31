"""
Popups as their own object.

The thing worth testing hardest is that a popup can exist with no form at all
— that is what separated it from a Form in the first place — and that the one
with a form still does everything a form submission does.
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, User
from apps.forms.models import Form
from apps.popups.models import Popup, PopupTemplate


class PopupApiTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse('popups:popup-list')

    def _detail(self, popup, suffix=''):
        url = reverse('popups:popup-detail', args=[popup.id])
        return f'{url}{suffix}' if suffix else url

    def _popup(self, **kwargs):
        kwargs.setdefault('organization', self.org)
        kwargs.setdefault('name', 'Newsletter')
        kwargs.setdefault('cta_text', 'Subscribe')
        return Popup.objects.create(**kwargs)

    # ------------------------------------------------------------- create
    def test_an_announcement_needs_no_form(self):
        """The reason a popup is not a Form."""
        response = self.client.post(self.list_url, {
            'name': 'Summit',
            'popup_type': 'floating_bar',
            'title': 'We are at the summit',
            'cta_text': 'Book a slot',
            'cta_url': 'https://acme.test/summit',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        popup = Popup.objects.get(name='Summit')
        self.assertIsNone(popup.form_id)
        self.assertEqual(popup.status, Popup.STATUS_DRAFT)

    def test_a_capture_popup_embeds_one_of_your_own_forms(self):
        form = Form.objects.create(organization=self.org, name='Signup')

        response = self.client.post(self.list_url, {
            'name': 'Capture', 'form': str(form.id),
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Popup.objects.get(name='Capture').form, form)

    def test_it_cannot_embed_another_accounts_form(self):
        other = Organization.objects.create(name='Other', slug='other')
        theirs = Form.objects.create(organization=other, name='Theirs')

        response = self.client.post(self.list_url, {
            'name': 'Sneaky', 'form': str(theirs.id),
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_response_carries_the_id(self):
        """Without it the client cannot open what it just made."""
        response = self.client.post(
            self.list_url, {'name': 'Thing', 'cta_text': 'Go'}, format='json',
        )
        self.assertEqual(
            str(response.data['id']), str(Popup.objects.get(name='Thing').id),
        )

    # ------------------------------------------------------------ publish
    def test_publishing_without_a_form_or_a_cta_is_refused(self):
        """A popup a visitor cannot act on is worse than no popup."""
        popup = self._popup(cta_text='')

        response = self.client.post(self._detail(popup, 'publish/'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_publishing_a_future_popup_schedules_it_instead(self):
        popup = self._popup(starts_at=timezone.now() + timedelta(days=2))

        response = self.client.post(self._detail(popup, 'publish/'))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        popup.refresh_from_db()
        self.assertEqual(popup.status, Popup.STATUS_SCHEDULED)
        self.assertFalse(popup.is_live())

    def test_publishing_a_popup_with_no_schedule_makes_it_live(self):
        popup = self._popup()

        self.client.post(self._detail(popup, 'publish/'))

        popup.refresh_from_db()
        self.assertEqual(popup.status, Popup.STATUS_PUBLISHED)
        self.assertTrue(popup.is_live())

    def test_pausing_takes_it_off_the_site(self):
        popup = self._popup(status=Popup.STATUS_PUBLISHED)

        self.client.post(self._detail(popup, 'pause/'))

        popup.refresh_from_db()
        self.assertEqual(popup.status, Popup.STATUS_PAUSED)
        self.assertFalse(popup.is_live())

    def test_an_end_date_in_the_past_is_not_live(self):
        popup = self._popup(
            status=Popup.STATUS_PUBLISHED,
            ends_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(popup.is_live())

    def test_the_end_must_come_after_the_start(self):
        now = timezone.now()
        response = self.client.post(self.list_url, {
            'name': 'Backwards', 'cta_text': 'Go',
            'starts_at': (now + timedelta(days=2)).isoformat(),
            'ends_at': (now + timedelta(days=1)).isoformat(),
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ends_at', response.data.get('details', response.data))

    # ---------------------------------------------------------- duplicate
    def test_a_duplicate_starts_as_a_draft_with_no_history(self):
        """
        Inheriting another popup's conversion rate would be a lie in the one
        place a marketer goes to compare them.
        """
        popup = self._popup(
            status=Popup.STATUS_PUBLISHED, impression_count=900,
            click_count=90, conversion_count=45,
        )

        response = self.client.post(self._detail(popup, 'duplicate/'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        copy = Popup.objects.get(name='Newsletter (copy)')
        self.assertEqual(copy.status, Popup.STATUS_DRAFT)
        self.assertEqual(copy.impression_count, 0)
        self.assertEqual(copy.conversion_count, 0)
        self.assertEqual(copy.triggers, popup.triggers)

    # ------------------------------------------------------------- delete
    def test_deleting_is_soft_so_a_live_popup_stops_rather_than_404s(self):
        popup = self._popup(status=Popup.STATUS_PUBLISHED)

        response = self.client.delete(self._detail(popup))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        popup.refresh_from_db()
        self.assertIsNotNone(popup.deleted_at)
        self.assertFalse(popup.is_live())

    # ---------------------------------------------------------- isolation
    def test_another_accounts_popups_are_not_listed(self):
        other = Organization.objects.create(name='Other', slug='other')
        Popup.objects.create(organization=other, name='Theirs', cta_text='Go')
        mine = self._popup()

        response = self.client.get(self.list_url)

        names = [row['name'] for row in response.data['results']]
        self.assertEqual(names, [mine.name])

    # ------------------------------------------------------------- rates
    def test_conversion_rate_counts_submissions_when_there_is_a_form(self):
        form = Form.objects.create(organization=self.org, name='Signup')
        popup = self._popup(
            form=form, impression_count=200, conversion_count=10, click_count=99,
        )
        self.assertEqual(popup.conversion_rate, 5.0)

    def test_conversion_rate_counts_clicks_when_there_is_not(self):
        """An announcement converts by being clicked; it has nothing to submit."""
        popup = self._popup(impression_count=200, click_count=10)
        self.assertEqual(popup.conversion_rate, 5.0)

    def test_a_popup_nobody_has_seen_reads_zero_not_an_error(self):
        self.assertEqual(self._popup().conversion_rate, 0.0)


class PopupTemplateTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.client.force_authenticate(user=self.user)

    def test_system_templates_are_offered_to_everyone(self):
        PopupTemplate.objects.create(
            name='Newsletter', is_system=True, category='newsletter',
        )
        response = self.client.get(reverse('popups:popup-template-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_another_accounts_saved_template_is_not_offered(self):
        other = Organization.objects.create(name='Other', slug='other')
        PopupTemplate.objects.create(name='Theirs', organization=other)

        response = self.client.get(reverse('popups:popup-template-list'))

        self.assertEqual(response.data['results'], [])

    def test_creating_from_a_template_copies_its_content_and_triggers(self):
        template = PopupTemplate.objects.create(
            name='Exit offer', is_system=True, category='exit_offer',
            popup_type=Popup.TYPE_MODAL,
            content={'title': 'Wait!', 'ctaText': 'Claim it'},
            triggers={'type': 'exit_intent', 'delaySeconds': 3},
        )

        response = self.client.post(reverse('popups:popup-list'), {
            'name': 'My exit offer', 'template_id': str(template.id),
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        popup = Popup.objects.get(name='My exit offer')
        self.assertEqual(popup.title, 'Wait!')
        self.assertEqual(popup.triggers['type'], 'exit_intent')
        template.refresh_from_db()
        self.assertEqual(template.usage_count, 1)

    def test_what_the_marketer_typed_beats_the_template(self):
        template = PopupTemplate.objects.create(
            name='Newsletter', is_system=True,
            content={'title': 'Join the list'},
        )

        self.client.post(reverse('popups:popup-list'), {
            'name': 'Mine', 'title': 'My own headline',
            'template_id': str(template.id),
        }, format='json')

        self.assertEqual(Popup.objects.get(name='Mine').title, 'My own headline')

    def test_an_unknown_template_is_refused(self):
        response = self.client.post(reverse('popups:popup-list'), {
            'name': 'Nope',
            'template_id': '00000000-0000-0000-0000-000000000000',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SeedTemplatesTests(APITestCase):
    def test_seeding_is_idempotent(self):
        """A deploy runs it every time; running twice must not duplicate."""
        from django.core.management import call_command

        call_command('seed_popup_templates', verbosity=0)
        first = PopupTemplate.objects.filter(is_system=True).count()
        call_command('seed_popup_templates', verbosity=0)

        self.assertEqual(PopupTemplate.objects.filter(is_system=True).count(), first)
        self.assertGreaterEqual(first, 5)

    def test_the_announcement_template_wants_no_form(self):
        """The template that proves a popup need not capture anything."""
        from django.core.management import call_command

        call_command('seed_popup_templates', verbosity=0)
        announcement = PopupTemplate.objects.get(name='Announcement bar')

        self.assertFalse(announcement.wants_form)
        self.assertEqual(announcement.popup_type, Popup.TYPE_FLOATING_BAR)
        self.assertFalse(announcement.design['backdrop'])

    def test_clearing_leaves_an_organizations_own_templates_alone(self):
        from django.core.management import call_command

        org = Organization.objects.create(name='Mine', slug='mine')
        mine = PopupTemplate.objects.create(name='Mine', organization=org)
        call_command('seed_popup_templates', verbosity=0)

        call_command('seed_popup_templates', '--clear', verbosity=0)

        self.assertEqual(PopupTemplate.objects.filter(is_system=True).count(), 0)
        self.assertTrue(PopupTemplate.objects.filter(pk=mine.pk).exists())
