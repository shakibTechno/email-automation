"""
Tests for Contact services.
"""
from django.test import TestCase
from apps.accounts.models import Organization, User
from apps.contacts.models import Contact, Tag, ContactTag
from apps.contacts.services import (
    CSVExportService,
    CSVImportService,
    DuplicateDetectionService
)
import io


class CSVExportServiceTest(TestCase):
    """Tests for CSVExportService."""

    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
        self.contact1 = Contact.objects.create(
            organization=self.organization,
            email='contact1@example.com',
            first_name='John',
            last_name='Doe',
            company='Company A'
        )
        self.contact2 = Contact.objects.create(
            organization=self.organization,
            email='contact2@example.com',
            first_name='Jane',
            last_name='Smith',
            company='Company B'
        )

    def test_export_contacts(self):
        """Test exporting contacts to CSV."""
        queryset = Contact.objects.all()
        csv_content = CSVExportService.export_contacts(queryset)

        self.assertIn('contact1@example.com', csv_content)
        self.assertIn('contact2@example.com', csv_content)
        self.assertIn('John', csv_content)
        self.assertIn('Jane', csv_content)

    def test_export_contacts_with_tags(self):
        """Test exporting contacts with tags."""
        tag = Tag.objects.create(
            organization=self.organization,
            name='Customer'
        )
        ContactTag.objects.create(contact=self.contact1, tag=tag)

        queryset = Contact.objects.all()
        csv_content = CSVExportService.export_contacts_with_tags(queryset)

        self.assertIn('tags', csv_content)
        self.assertIn('Customer', csv_content)


class CSVImportServiceTest(TestCase):
    """Tests for CSVImportService."""

    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            organization=self.organization
        )

    def test_import_contacts_from_csv(self):
        """Test importing contacts from CSV."""
        csv_content = """email,first_name,last_name,company
john@example.com,John,Doe,Company A
jane@example.com,Jane,Smith,Company B
"""
        csv_file = io.BytesIO(csv_content.encode('utf-8'))

        service = CSVImportService(self.organization, self.user)
        results = service.import_from_csv(csv_file)

        self.assertEqual(results['imported'], 2)
        self.assertEqual(results['skipped'], 0)
        self.assertEqual(Contact.objects.count(), 2)

    def test_import_with_duplicates(self):
        """Test importing with duplicate emails."""
        # Create existing contact
        Contact.objects.create(
            organization=self.organization,
            email='john@example.com',
            first_name='Existing',
            last_name='Contact'
        )

        csv_content = """email,first_name,last_name,company
john@example.com,John,Doe,Company A
jane@example.com,Jane,Smith,Company B
"""
        csv_file = io.BytesIO(csv_content.encode('utf-8'))

        service = CSVImportService(self.organization, self.user)
        results = service.import_from_csv(csv_file, skip_duplicates=True)

        self.assertEqual(results['imported'], 1)
        self.assertEqual(results['skipped'], 1)
        self.assertEqual(Contact.objects.count(), 2)

    def test_import_update_existing(self):
        """Test importing and updating existing contacts."""
        # Create existing contact
        Contact.objects.create(
            organization=self.organization,
            email='john@example.com',
            first_name='Existing',
            last_name='Contact'
        )

        csv_content = """email,first_name,last_name,company
john@example.com,John,Doe,Company A
"""
        csv_file = io.BytesIO(csv_content.encode('utf-8'))

        service = CSVImportService(self.organization, self.user)
        results = service.import_from_csv(csv_file, update_existing=True)

        self.assertEqual(results['updated'], 1)
        self.assertEqual(results['imported'], 0)

        contact = Contact.objects.get(email='john@example.com')
        self.assertEqual(contact.first_name, 'John')
        self.assertEqual(contact.company, 'Company A')

    def test_import_with_custom_field_mapping(self):
        """Test importing with custom field mapping."""
        csv_content = """Email Address,First,Last,Org
john@example.com,John,Doe,Company A
"""
        csv_file = io.BytesIO(csv_content.encode('utf-8'))

        field_mapping = {
            'Email Address': 'email',
            'First': 'first_name',
            'Last': 'last_name',
            'Org': 'company'
        }

        service = CSVImportService(self.organization, self.user)
        results = service.import_from_csv(csv_file, field_mapping=field_mapping)

        self.assertEqual(results['imported'], 1)
        contact = Contact.objects.get(email='john@example.com')
        self.assertEqual(contact.first_name, 'John')


class DuplicateDetectionServiceTest(TestCase):
    """Tests for DuplicateDetectionService."""

    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )

    def test_find_duplicates_by_email(self):
        """Test finding duplicate contacts by email."""
        # Note: Due to unique constraint on (organization, email),
        # we can't create true duplicates. In real scenarios, duplicates
        # would only occur if the constraint was added later or data
        # was imported before validation was in place.
        # This test verifies the service works when there are no duplicates.

        # Create unique contacts
        Contact.objects.create(
            organization=self.organization,
            email='contact1@example.com',
            first_name='First'
        )
        Contact.objects.create(
            organization=self.organization,
            email='contact2@example.com',
            first_name='Second'
        )

        duplicate_groups = DuplicateDetectionService.find_duplicates_by_email(
            self.organization
        )

        # Should find no duplicates
        self.assertEqual(len(duplicate_groups), 0)

    def test_find_similar_contacts(self):
        """Test finding similar contacts."""
        Contact.objects.create(
            organization=self.organization,
            email='john@example.com',
            first_name='John',
            last_name='Doe'
        )

        similar = DuplicateDetectionService.find_similar_contacts(
            self.organization,
            email='john@example.com'
        )

        self.assertEqual(len(similar), 1)

    def test_merge_contacts(self):
        """Test merging duplicate contacts."""
        # Create contacts with different emails for testing merge logic
        primary = Contact.objects.create(
            organization=self.organization,
            email='primary@example.com',
            first_name='Primary',
            lead_score=50
        )
        duplicate1 = Contact.objects.create(
            organization=self.organization,
            email='duplicate1@example.com',
            first_name='Duplicate1',
            lead_score=75,
            custom_fields={'field1': 'value1'}
        )
        duplicate2 = Contact.objects.create(
            organization=self.organization,
            email='duplicate2@example.com',
            first_name='Duplicate2',
            custom_fields={'field2': 'value2'}
        )

        merged = DuplicateDetectionService.merge_contacts(
            primary,
            [duplicate1, duplicate2]
        )

        self.assertEqual(merged.lead_score, 75)  # Highest score
        self.assertIn('field1', merged.custom_fields)
        self.assertIn('field2', merged.custom_fields)

        # Duplicates should be soft deleted
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Contact.all_objects.count(), 3)
