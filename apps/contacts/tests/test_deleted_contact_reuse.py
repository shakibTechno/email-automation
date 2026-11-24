"""
A deleted contact still owns its address.

`Contact.objects` hides a soft-deleted row; the unique index on
(organization, email) counts it. Every path that asked the manager "is there
already a contact?" got "no" and tried the insert, which the database refused
— so the same person could never come back through a public form. The report
was plain enough: "I can't submit the form with same email."
"""
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization
from apps.contacts.models import Contact
from apps.forms.models import Form, FormField
from apps.forms.services import FormSubmissionService


class ClaimTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')

    def test_a_new_address_creates_a_contact(self):
        contact, created = Contact.objects.claim(
            self.org, 'new@example.com', first_name='Ada'
        )

        self.assertTrue(created)
        self.assertEqual(contact.first_name, 'Ada')

    def test_an_existing_contact_is_returned_not_duplicated(self):
        first, _ = Contact.objects.claim(self.org, 'ada@example.com')

        second, created = Contact.objects.claim(self.org, 'ada@example.com')

        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Contact.all_objects.count(), 1)

    def test_a_deleted_contact_comes_back(self):
        contact, _ = Contact.objects.claim(self.org, 'ada@example.com')
        contact.deleted_at = timezone.now()
        contact.save(update_fields=['deleted_at'])

        revived, created = Contact.objects.claim(self.org, 'ada@example.com')

        self.assertFalse(created, 'a revived contact is not a new one')
        self.assertEqual(revived.pk, contact.pk)
        self.assertIsNone(revived.deleted_at)
        self.assertEqual(Contact.all_objects.count(), 1)

    def test_reviving_does_not_undo_an_unsubscribe(self):
        """
        Filling in a form is a reason to talk to someone again. It is not
        their consent to start mailing them after they opted out.
        """
        contact, _ = Contact.objects.claim(self.org, 'ada@example.com')
        contact.unsubscribe()
        contact.deleted_at = timezone.now()
        contact.save(update_fields=['deleted_at'])

        revived, _ = Contact.objects.claim(self.org, 'ada@example.com')

        self.assertFalse(revived.is_subscribed)
        self.assertIsNotNone(revived.unsubscribed_at)

    def test_another_organizations_contact_is_not_claimed(self):
        other = Organization.objects.create(name='Other', slug='other')
        theirs, _ = Contact.objects.claim(other, 'ada@example.com')

        mine, created = Contact.objects.claim(self.org, 'ada@example.com')

        self.assertTrue(created)
        self.assertNotEqual(mine.pk, theirs.pk)


class FormResubmissionTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.form = Form.objects.create(
            organization=self.org, name='Lead Collection', status='active',
        )
        self.email_field = FormField.objects.create(
            form=self.form, label='Email', field_type='email',
            contact_field_mapping='email', order=0,
        )
        self.name_field = FormField.objects.create(
            form=self.form, label='First name', contact_field_mapping='first_name',
            order=1,
        )

    def submit(self, email, name='Ada'):
        return FormSubmissionService.process_submission(
            self.form,
            {str(self.email_field.id): email, str(self.name_field.id): name},
        )

    def test_the_same_address_can_submit_twice(self):
        first = self.submit('ada@example.com')
        second = self.submit('ada@example.com', name='Ada L')

        self.assertNotEqual(first.id, second.id, 'both submissions are kept')
        self.assertEqual(Contact.objects.filter(organization=self.org).count(), 1)
        self.assertEqual(second.contact.first_name, 'Ada L')

    def test_the_same_address_can_submit_after_its_contact_was_deleted(self):
        first = self.submit('ada@example.com')
        contact = first.contact
        contact.deleted_at = timezone.now()
        contact.save(update_fields=['deleted_at'])

        second = self.submit('ada@example.com', name='Ada Again')

        self.assertIsNotNone(second.contact, 'the lead was lost')
        self.assertEqual(second.contact.pk, contact.pk)
        self.assertIsNone(second.contact.deleted_at)
        self.assertEqual(second.contact.first_name, 'Ada Again')

    def test_both_submissions_survive_the_deletion(self):
        """The enquiries are the record; deleting the person does not erase them."""
        self.submit('ada@example.com')
        contact = Contact.objects.get(organization=self.org, email='ada@example.com')
        contact.deleted_at = timezone.now()
        contact.save(update_fields=['deleted_at'])

        self.submit('ada@example.com')

        self.assertEqual(self.form.submissions.count(), 2)
