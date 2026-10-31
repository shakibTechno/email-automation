"""
The script a customer puts on their own website.

It is fetched by a `<script src>` on a page we do not serve, so the two things
that matter are that it is always valid JavaScript and that it only ever
carries one organization's popups.
"""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Organization, User
from apps.popups.models import Popup


class SnippetTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.url = reverse('tracking:snippet')

    def _popup(self, **kwargs):
        kwargs.setdefault('organization', self.org)
        kwargs.setdefault('name', 'Newsletter')
        kwargs.setdefault('status', Popup.STATUS_PUBLISHED)
        kwargs.setdefault('popup_type', Popup.TYPE_MODAL)
        kwargs.setdefault('cta_text', 'Subscribe')
        return Popup.objects.create(**kwargs)

    def _get(self, key=None):
        key = self.org.tracking_key if key is None else key
        return self.client.get(self.url, {'k': str(key)})

    # ------------------------------------------------------------ contract
    def test_it_is_served_as_javascript(self):
        self._popup()
        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')

    def test_an_unknown_key_is_still_javascript(self):
        """
        A 404 page where a site expects a script is a syntax error in the
        visitor's console. An empty script is a no-op nobody notices.
        """
        response = self._get(key='00000000-0000-0000-0000-000000000000')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertIn('mailflow', response.content.decode())

    def test_a_key_that_is_not_a_uuid_is_answered_the_same_way(self):
        """Nothing in the response may say which keys exist."""
        unknown = self._get(key='00000000-0000-0000-0000-000000000000')
        garbage = self._get(key='not-a-uuid')

        self.assertEqual(garbage.status_code, unknown.status_code)
        self.assertEqual(garbage.content, unknown.content)

    def test_a_missing_key_does_not_raise(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    # ------------------------------------------------------------- content
    def test_a_published_popup_is_included_with_its_content(self):
        popup = self._popup(
            title='Join the list', description='Monthly, no spam.',
            cta_text='Subscribe',
            triggers={'type': 'scroll', 'scrollPercent': 70},
        )
        body = self._get().content.decode()

        self.assertIn(str(popup.id), body)
        self.assertIn('Join the list', body)
        self.assertIn('scroll', body)
        self.assertIn('70', body)

    def test_an_announcement_without_a_form_is_served(self):
        """A popup need not capture anything."""
        popup = self._popup(title='We are at the summit', cta_text='Book a slot',
                            cta_url='https://acme.test/summit')
        body = self._get().content.decode()

        self.assertIn(str(popup.id), body)
        self.assertIn('"formId":null', body.replace(' ', ''))

    def test_a_capture_popup_names_its_form(self):
        from apps.forms.models import Form

        form = Form.objects.create(
            organization=self.org, name='Signup', status='active',
        )
        self._popup(form=form)

        self.assertIn(str(form.id), self._get().content.decode())

    def test_every_popup_type_is_served(self):
        made = [
            self._popup(name=label, popup_type=value)
            for value, label in Popup.TYPE_CHOICES
        ]
        body = self._get().content.decode()

        for popup in made:
            self.assertIn(str(popup.id), body, popup.popup_type)

    # -------------------------------------------------------------- status
    def test_a_draft_is_not_served(self):
        draft = self._popup(name='Draft', status=Popup.STATUS_DRAFT)
        self.assertNotIn(str(draft.id), self._get().content.decode())

    def test_a_paused_popup_is_not_served(self):
        paused = self._popup(name='Paused', status=Popup.STATUS_PAUSED)
        self.assertNotIn(str(paused.id), self._get().content.decode())

    def test_a_deleted_popup_is_not_served(self):
        popup = self._popup()
        popup.soft_delete()
        self.assertNotIn(str(popup.id), self._get().content.decode())

    # ------------------------------------------------------------ schedule
    def test_a_popup_whose_start_is_in_the_future_is_not_served(self):
        future = self._popup(starts_at=timezone.now() + timedelta(days=1))
        self.assertNotIn(str(future.id), self._get().content.decode())

    def test_a_popup_whose_end_has_passed_is_not_served(self):
        """
        Decided on the server. A visitor with a wrong clock must not be able
        to resurrect an expired campaign.
        """
        expired = self._popup(ends_at=timezone.now() - timedelta(minutes=1))
        self.assertNotIn(str(expired.id), self._get().content.decode())

    def test_a_popup_inside_its_window_is_served(self):
        live = self._popup(
            starts_at=timezone.now() - timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1),
        )
        self.assertIn(str(live.id), self._get().content.decode())

    # ----------------------------------------------------------- isolation
    def test_another_organizations_popups_are_never_included(self):
        other = Organization.objects.create(name='Other', slug='other')
        theirs = Popup.objects.create(
            organization=other, name='Theirs', status=Popup.STATUS_PUBLISHED,
            cta_text='Go',
        )
        mine = self._popup()

        body = self._get().content.decode()

        self.assertIn(str(mine.id), body)
        self.assertNotIn(str(theirs.id), body)

    def test_each_organization_gets_a_distinct_key(self):
        other = Organization.objects.create(name='Other', slug='other')
        self.assertNotEqual(self.org.tracking_key, other.tracking_key)

    def test_an_inactive_organization_gets_nothing(self):
        self._popup()
        self.org.is_active = False
        self.org.save(update_fields=['is_active'])

        self.assertNotIn('popups', self._get().content.decode())

    # -------------------------------------------------------------- safety
    def test_content_cannot_close_the_script_tag(self):
        self._popup(title='</script><script>evil()')

        body = self._get().content.decode()

        self.assertNotIn('</script>', body)
        self.assertIn('\\u003c', body)

    def test_nothing_is_served_when_there_are_no_popups(self):
        body = self._get().content.decode()
        self.assertIn('"popups":[]', body.replace(' ', ''))
