"""
The script a customer puts on their own website.

It is fetched by a `<script src>` on a page we do not serve, so the two things
that matter are that it is always valid JavaScript and that it only ever
carries one organization's popups.
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Organization, User
from apps.forms.models import Form, default_display_rules


class SnippetTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.url = reverse('tracking:snippet')

    def _form(self, **kwargs):
        kwargs.setdefault('organization', self.org)
        kwargs.setdefault('name', 'Newsletter')
        kwargs.setdefault('status', 'active')
        kwargs.setdefault('form_type', 'popup')
        return Form.objects.create(**kwargs)

    def _get(self, key=None):
        key = self.org.tracking_key if key is None else key
        return self.client.get(self.url, {'k': str(key)})

    # ------------------------------------------------------------ contract
    def test_it_is_served_as_javascript(self):
        self._form()
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
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------- content
    def test_an_active_popup_is_included_with_its_rules(self):
        form = self._form(display_rules={**default_display_rules(),
                                         'trigger': 'scroll',
                                         'scrollPercent': 70})
        body = self._get().content.decode()

        self.assertIn(str(form.id), body)
        self.assertIn('scroll', body)
        self.assertIn('70', body)

    def test_inline_forms_are_not_popups(self):
        inline = self._form(name='Contact us', form_type='inline')
        popup = self._form(name='Newsletter', form_type='popup')

        body = self._get().content.decode()

        self.assertIn(str(popup.id), body)
        self.assertNotIn(str(inline.id), body)

    def test_an_inactive_popup_is_not_served(self):
        draft = self._form(name='Draft', status='inactive')
        self.assertNotIn(str(draft.id), self._get().content.decode())

    def test_slide_in_and_top_bar_count_as_popups(self):
        slide = self._form(name='Slide', form_type='slide_in')
        bar = self._form(name='Bar', form_type='top_bar')

        body = self._get().content.decode()

        self.assertIn(str(slide.id), body)
        self.assertIn(str(bar.id), body)

    # ----------------------------------------------------------- isolation
    def test_another_organizations_popups_are_never_included(self):
        other = Organization.objects.create(name='Other', slug='other')
        theirs = Form.objects.create(
            organization=other, name='Theirs', status='active',
            form_type='popup',
        )
        mine = self._form()

        body = self._get().content.decode()

        self.assertIn(str(mine.id), body)
        self.assertNotIn(str(theirs.id), body)

    def test_each_organization_gets_a_distinct_key(self):
        other = Organization.objects.create(name='Other', slug='other')
        self.assertNotEqual(self.org.tracking_key, other.tracking_key)

    def test_an_inactive_organization_gets_nothing(self):
        self._form()
        self.org.is_active = False
        self.org.save(update_fields=['is_active'])

        self.assertNotIn('popups', self._get().content.decode())

    # -------------------------------------------------------------- safety
    def test_the_config_cannot_close_the_script_tag(self):
        """
        The script is inlined into a response, not a page, but a `</script>`
        reaching a customer's HTML through a copied snippet would end it early.
        """
        self._form(display_rules={**default_display_rules(),
                                  'clickSelector': '</script><script>evil()'})

        body = self._get().content.decode()

        self.assertNotIn('</script>', body)
        self.assertIn('\\u003c', body)

    def test_nothing_is_served_when_there_are_no_popups(self):
        body = self._get().content.decode()
        # The script bails immediately rather than installing listeners.
        self.assertIn('"popups":[]', body.replace(' ', ''))
