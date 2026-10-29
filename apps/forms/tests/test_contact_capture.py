"""
What a form submission puts on the contact, and what it leaves behind.

A question that maps to a contact field becomes a value on the contact. One
that maps to a custom field becomes a value in custom_fields. One that maps to
nothing stays on the submission -- and is still readable from the contact's
timeline, because it is usually the answer that mattered.
"""
from django.test import TestCase

from apps.accounts.models import Organization
from apps.contacts.models import Contact, CustomField
from apps.contacts.services import ActivityTimelineService


def _timeline_events(contact):
    """ActivityTimelineService is defined twice in that module and the
    second shadows the first; the two disagree on the return shape."""
    result = ActivityTimelineService.get_timeline(contact)
    return result['results'] if isinstance(result, dict) else result
from apps.forms.models import Form, FormField, FormSubmission
from apps.forms.services import FormSubmissionService


class ContactCaptureTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.form = Form.objects.create(
            organization=self.org, name='Demo request', status='active',
        )
        CustomField.objects.create(
            organization=self.org, key='budget', name='Budget', field_type='text',
        )

    def _field(self, label, mapping='', order=0, field_type='text'):
        return FormField.objects.create(
            form=self.form, label=label, field_type=field_type,
            contact_field_mapping=mapping, order=order,
        )

    def _submit(self, pairs):
        """pairs: [(field, value)] -> the upserted contact."""
        data = {str(field.id): value for field, value in pairs}
        fields_by_id = {str(field.id): field for field, _ in pairs}
        return FormSubmissionService.upsert_contact(self.org, fields_by_id, data)

    # ------------------------------------------------------------- standard
    def test_a_standard_mapping_lands_on_the_contact(self):
        email = self._field('Email', 'email', 0, 'email')
        name = self._field('First name', 'first_name', 1)

        contact = self._submit([(email, 'ada@example.com'), (name, 'Ada')])

        self.assertEqual(contact.email, 'ada@example.com')
        self.assertEqual(contact.first_name, 'Ada')

    def test_a_field_beyond_the_original_six_is_captured(self):
        """
        The builder offered six mappings while the model had far more, so
        anything added to the contact could not be collected by a form.
        """
        email = self._field('Email', 'email', 0, 'email')
        city = self._field('City', 'city', 1)

        contact = self._submit([(email, 'ada@example.com'), (city, 'Dublin')])

        self.assertEqual(contact.city, 'Dublin')

    # --------------------------------------------------------------- custom
    def test_a_custom_mapping_lands_in_custom_fields(self):
        email = self._field('Email', 'email', 0, 'email')
        budget = self._field('Budget', 'custom.budget', 1)

        contact = self._submit([(email, 'ada@example.com'), (budget, '25k')])

        self.assertEqual(contact.custom_fields.get('budget'), '25k')

    def test_a_second_submission_merges_rather_than_replaces(self):
        email = self._field('Email', 'email', 0, 'email')
        budget = self._field('Budget', 'custom.budget', 1)
        CustomField.objects.create(
            organization=self.org, key='timeline', name='Timeline', field_type='text',
        )
        timeline = self._field('Timeline', 'custom.timeline', 2)

        self._submit([(email, 'ada@example.com'), (budget, '25k')])
        contact = self._submit([(email, 'ada@example.com'), (timeline, 'Q3')])

        self.assertEqual(contact.custom_fields.get('budget'), '25k')
        self.assertEqual(contact.custom_fields.get('timeline'), 'Q3')

    def test_an_undefined_custom_field_does_not_cost_the_lead(self):
        """One bad answer must not throw away the contact."""
        email = self._field('Email', 'email', 0, 'email')
        unknown = self._field('Shoe size', 'custom.shoe_size', 1)

        contact = self._submit([(email, 'ada@example.com'), (unknown, '42')])

        self.assertIsNotNone(contact)
        self.assertEqual(contact.email, 'ada@example.com')
        self.assertNotIn('shoe_size', contact.custom_fields)

    # -------------------------------------------------------------- refusal
    def test_a_mapping_a_form_may_not_write_is_ignored(self):
        email = self._field('Email', 'email', 0, 'email')
        sneaky = self._field('Org', 'organization_id', 1)
        other = Organization.objects.create(name='Other', slug='other')

        contact = self._submit([(email, 'ada@example.com'), (sneaky, str(other.id))])

        self.assertEqual(contact.organization_id, self.org.id)

    def test_without_an_email_mapping_no_contact_is_made(self):
        """Nothing distinguishes two submissions without one."""
        name = self._field('First name', 'first_name', 0)

        self.assertIsNone(self._submit([(name, 'Ada')]))

    # ------------------------------------------------------------- timeline
    def test_unmapped_answers_are_readable_from_the_contact(self):
        email = self._field('Email', 'email', 0, 'email')
        heard = self._field('How did you hear about us?', '', 1)

        contact = self._submit([(email, 'ada@example.com'), (heard, 'A colleague')])
        FormSubmission.objects.create(
            form=self.form, contact=contact,
            data={str(email.id): 'ada@example.com', str(heard.id): 'A colleague'},
        )

        timeline = _timeline_events(contact)
        entry = next(e for e in timeline if e['type'] == 'form_submission')
        answers = entry['metadata']['answers']

        self.assertIn(
            {'label': 'How did you hear about us?', 'value': 'A colleague',
             'mapped': False},
            answers,
        )

    def test_the_timeline_says_which_answers_reached_the_contact(self):
        email = self._field('Email', 'email', 0, 'email')
        heard = self._field('How did you hear about us?', '', 1)

        contact = self._submit([(email, 'ada@example.com'), (heard, 'A colleague')])
        FormSubmission.objects.create(
            form=self.form, contact=contact,
            data={str(email.id): 'ada@example.com', str(heard.id): 'A colleague'},
        )

        entry = next(
            e for e in _timeline_events(contact)
            if e['type'] == 'form_submission'
        )
        by_label = {a['label']: a['mapped'] for a in entry['metadata']['answers']}

        self.assertTrue(by_label['Email'])
        self.assertFalse(by_label['How did you hear about us?'])


class ContactFieldOptionsTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')

    def test_the_options_cover_more_than_the_six_the_builder_hardcoded(self):
        options = FormSubmissionService.contact_field_options(self.org)
        values = {o['value'] for o in options}

        self.assertTrue({'first_name', 'last_name', 'email', 'phone'} <= values)
        self.assertGreater(len(values), 6, 'the registry has far more than six')

    def test_custom_fields_are_offered_too(self):
        CustomField.objects.create(
            organization=self.org, key='budget', name='Budget', field_type='text',
        )

        options = FormSubmissionService.contact_field_options(self.org)
        custom = [o for o in options if o['group'] == 'Custom fields']

        self.assertEqual(
            custom, [{'value': 'custom.budget', 'label': 'Budget',
                      'group': 'Custom fields'}],
        )

    def test_another_organizations_custom_fields_are_not_offered(self):
        other = Organization.objects.create(name='Other', slug='other')
        CustomField.objects.create(
            organization=other, key='secret', name='Secret', field_type='text',
        )

        values = {
            o['value'] for o in FormSubmissionService.contact_field_options(self.org)
        }
        self.assertNotIn('custom.secret', values)
