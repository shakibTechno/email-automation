"""
The contact field registry, and the write paths it closes.

Three places used to assign to whatever attribute name they were handed. The
first of these tests is the reason this work was staged with the security fix
first: a CSV import could write contacts into another tenant's organization.
"""
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.contacts import fields as contact_fields
from apps.contacts.models import Contact
from apps.contacts.services import CSVExportService, CSVImportService


def csv_upload(content, name='contacts.csv'):
    return SimpleUploadedFile(name, content.encode(), content_type='text/csv')


class ImportMappingIsolationTests(TestCase):
    """
    A crafted import must not reach fields it was never offered.

    `field_mapping` is a free-form JSONField on the request. The importer took
    its values as model attribute names, so mapping a column to
    `organization_id` moved the created contacts into another tenant. The UI
    only ever offered six safe targets; nothing stopped a hand-made request.
    """

    def setUp(self):
        self.mine = Organization.objects.create(name='Mine', slug='mine')
        self.theirs = Organization.objects.create(name='Theirs', slug='theirs')
        self.user = User.objects.create_user(
            email='me@mine.test', password='x', organization=self.mine, role='owner',
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def _import(self, mapping, csv_text='email,col\nnew@example.com,value\n'):
        return self.api.post(
            '/api/v1/contacts/import_csv/',
            {'file': csv_upload(csv_text), 'field_mapping': json.dumps(mapping)},
            format='multipart',
        )

    def test_mapping_a_column_to_organization_is_refused(self):
        """The hole. Nothing may relocate a contact to another tenant."""
        response = self._import({'email': 'email', 'col': 'organization_id'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Contact.objects.filter(organization=self.theirs).count(), 0)

    def test_no_contact_lands_in_another_organization(self):
        self._import({'email': 'email', 'col': 'organization'})

        self.assertFalse(
            Contact.all_objects.filter(organization=self.theirs).exists(),
            'a contact was written into another tenant',
        )

    def test_protected_internals_are_refused(self):
        for target in ('id', 'deleted_at', 'custom_fields', 'assigned_to_id'):
            with self.subTest(target=target):
                response = self._import({'email': 'email', 'col': target})
                self.assertEqual(response.status_code, 400, target)

    def test_engine_owned_fields_are_refused(self):
        """
        lead_score and engagement_level belong to the scoring engine. A CSV
        that could set them would make the number mean nothing.
        """
        for target in ('lead_score', 'engagement_level'):
            with self.subTest(target=target):
                response = self._import({'email': 'email', 'col': target})
                self.assertEqual(response.status_code, 400, target)

    def test_subscription_cannot_be_resurrected_by_an_import(self):
        """The one with legal consequences: a CSV must not re-subscribe anyone."""
        response = self._import({'email': 'email', 'col': 'is_subscribed'})

        self.assertEqual(response.status_code, 400)

    def test_the_error_names_the_offending_column(self):
        response = self._import({'email': 'email', 'col': 'organization_id'})

        # custom_exception_handler nests field errors under `details`.
        details = response.data['details']['field_mapping']
        self.assertIn('col', details)
        self.assertIn('organization_id', str(details['col']))

    def test_a_legitimate_mapping_still_works(self):
        response = self._import(
            {'email': 'email', 'col': 'company'},
            csv_text='email,col\nnew@example.com,Acme\n',
        )

        self.assertEqual(response.status_code, 200)
        contact = Contact.objects.get(email='new@example.com')
        self.assertEqual(contact.organization, self.mine)
        self.assertEqual(contact.company, 'Acme')

    def test_a_custom_field_target_is_accepted_and_stored_as_json(self):
        response = self._import(
            {'email': 'email', 'col': 'custom.industry'},
            csv_text='email,col\nnew@example.com,Mining\n',
        )

        self.assertEqual(response.status_code, 200)
        contact = Contact.objects.get(email='new@example.com')
        self.assertEqual(contact.custom_fields.get('industry'), 'Mining')


class ImportCoercionTests(TestCase):
    """A CSV cell is a string; the column it lands in often is not."""

    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        self.user = User.objects.create_user(
            email='me@mine.test', password='x', organization=self.org, role='owner',
        )

    def test_an_existing_contacts_other_custom_fields_survive_an_import(self):
        """
        Merged, not replaced. A CSV carrying one custom column used to be able
        to wipe every other custom value the contact held.
        """
        Contact.objects.create(
            organization=self.org, email='old@example.com',
            custom_fields={'industry': 'Mining', 'tier': 'gold'},
        )
        service = CSVImportService(organization=self.org, user=self.user)

        service.import_from_csv(
            csv_file=csv_upload('email,col\nold@example.com,Retail\n'),
            field_mapping={'email': 'email', 'col': 'custom.industry'},
            update_existing=True,
            skip_duplicates=False,
        )

        contact = Contact.objects.get(email='old@example.com')
        self.assertEqual(contact.custom_fields['industry'], 'Retail')
        self.assertEqual(contact.custom_fields['tier'], 'gold')


class ExportRestrictionTests(TestCase):
    """`getattr` with caller-supplied names reads more than it should."""

    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        Contact.objects.create(organization=self.org, email='a@example.com')

    def test_non_exportable_names_are_dropped(self):
        csv_text = CSVExportService.export_contacts(
            Contact.objects.filter(organization=self.org),
            fields=['email', 'organization_id', 'deleted_at'],
        )

        header = csv_text.splitlines()[0]
        self.assertIn('email', header)
        self.assertNotIn('organization_id', header)
        self.assertNotIn('deleted_at', header)


class RegistryContractTests(TestCase):
    """
    What stops a seventh hand-maintained list appearing.

    Six places each kept their own idea of the contact's shape, and they had
    already drifted — the segment builder offered a "Status" field the model has
    never had. These assert the derived lists stay derived.
    """

    def test_every_registry_key_is_a_real_model_field(self):
        model_fields = {f.name for f in Contact._meta.get_fields()}
        model_fields |= {
            f.attname for f in Contact._meta.get_fields() if hasattr(f, 'attname')
        }

        unknown = sorted(set(contact_fields.CONTACT_FIELDS) - model_fields)

        self.assertEqual(
            unknown, [],
            f'the registry declares fields the Contact model does not have: {unknown}',
        )

    def test_every_segmentable_field_resolves_in_a_query(self):
        """
        The guard for the bug that was already live. Each segmentable key is
        used in a real filter; a name the ORM cannot resolve raises here rather
        than in production.
        """
        from apps.segments.evaluator import FIELD_DEFINITIONS

        for key in FIELD_DEFINITIONS:
            if key == 'tag':
                continue  # not a column; handled by its own branch
            with self.subTest(field=key):
                # .exists() forces the SQL to be built and validated.
                Contact.objects.filter(**{f'{key}__isnull': True}).exists()

    def test_the_form_mapping_choices_come_from_the_registry(self):
        from apps.forms.models import FormField

        offered = {key for key, _ in FormField.CONTACT_FIELD_MAPPING_CHOICES if key}

        self.assertEqual(offered, contact_fields.writable_keys(contact_fields.FORM))

    def test_nothing_protected_is_writable_by_any_channel(self):
        for channel in (contact_fields.IMPORT, contact_fields.FORM, contact_fields.WORKFLOW):
            with self.subTest(channel=channel):
                overlap = contact_fields.writable_keys(channel) & contact_fields.NEVER_WRITABLE
                self.assertEqual(overlap, set())

    def test_a_field_absent_from_the_registry_is_not_writable(self):
        """Writability is opt-in; the old default was the opposite."""
        self.assertIsNotNone(
            contact_fields.rejection_reason('organization_id', contact_fields.IMPORT)
        )
        self.assertIsNotNone(
            contact_fields.rejection_reason('made_up_field', contact_fields.IMPORT)
        )


class CoercionTests(TestCase):
    def test_numbers_dates_and_booleans_are_converted(self):
        self.assertEqual(contact_fields.coerce_value('number', '42'), 42)
        self.assertEqual(contact_fields.coerce_value('number', '4.5'), 4.5)
        self.assertIs(contact_fields.coerce_value('boolean', 'yes'), True)
        self.assertIs(contact_fields.coerce_value('boolean', 'unsubscribed'), False)
        self.assertEqual(
            str(contact_fields.coerce_value('date', '2026-01-31')), '2026-01-31',
        )

    def test_an_empty_cell_becomes_none_rather_than_a_blank_number(self):
        self.assertIsNone(contact_fields.coerce_value('number', '   '))

    def test_a_bad_value_names_the_field(self):
        with self.assertRaises(contact_fields.CoercionError) as caught:
            contact_fields.coerce_value('number', 'lots', label='Lead Score')

        self.assertIn('Lead Score', str(caught.exception))

    def test_a_select_value_outside_its_options_is_refused(self):
        with self.assertRaises(contact_fields.CoercionError):
            contact_fields.coerce_value(
                'select', 'platinum', label='Source', options=('manual', 'import'),
            )
