"""
Tests for Contact models.
"""
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import Organization, User
from apps.contacts.models import Contact, Tag, ContactTag, CustomField
import uuid


class ContactModelTest(TestCase):
    """Tests for Contact model."""

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
        self.contact = Contact.objects.create(
            organization=self.organization,
            email='contact@example.com',
            first_name='John',
            last_name='Doe',
            company='Test Company'
        )

    def test_contact_creation(self):
        """Test contact is created correctly."""
        self.assertEqual(self.contact.email, 'contact@example.com')
        self.assertEqual(self.contact.first_name, 'John')
        self.assertEqual(self.contact.last_name, 'Doe')
        self.assertEqual(self.contact.company, 'Test Company')
        self.assertTrue(self.contact.is_subscribed)
        self.assertEqual(self.contact.lead_score, 0)

    def test_contact_full_name(self):
        """Test full_name property."""
        self.assertEqual(self.contact.full_name, 'John Doe')

        # Test with only email
        contact2 = Contact.objects.create(
            organization=self.organization,
            email='nofullname@example.com'
        )
        self.assertEqual(contact2.full_name, 'nofullname@example.com')

    def test_contact_unique_email_per_organization(self):
        """Test email uniqueness constraint per organization."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Contact.objects.create(
                organization=self.organization,
                email='contact@example.com'  # Duplicate email
            )

    def test_contact_unsubscribe(self):
        """Test unsubscribe method."""
        self.assertTrue(self.contact.is_subscribed)
        self.assertIsNone(self.contact.unsubscribed_at)

        self.contact.unsubscribe()

        self.assertFalse(self.contact.is_subscribed)
        self.assertIsNotNone(self.contact.unsubscribed_at)

    def test_contact_resubscribe(self):
        """Test resubscribe method."""
        self.contact.unsubscribe()
        self.assertFalse(self.contact.is_subscribed)

        self.contact.resubscribe()

        self.assertTrue(self.contact.is_subscribed)
        self.assertIsNone(self.contact.unsubscribed_at)

    def test_contact_soft_delete(self):
        """Test soft delete functionality."""
        self.assertIsNone(self.contact.deleted_at)

        self.contact.soft_delete()

        self.assertIsNotNone(self.contact.deleted_at)
        self.assertTrue(self.contact.is_deleted)  # Marked as deleted

        # Should not appear in default queryset
        self.assertEqual(Contact.objects.count(), 0)

        # Should appear in all_objects queryset
        self.assertEqual(Contact.all_objects.count(), 1)

    def test_contact_custom_fields(self):
        """Test custom fields JSONField."""
        self.contact.custom_fields = {
            'industry': 'Technology',
            'website': 'https://example.com'
        }
        self.contact.save()

        contact = Contact.objects.get(id=self.contact.id)
        self.assertEqual(contact.custom_fields['industry'], 'Technology')
        self.assertEqual(contact.custom_fields['website'], 'https://example.com')


class TagModelTest(TestCase):
    """Tests for Tag model."""

    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
        self.tag = Tag.objects.create(
            organization=self.organization,
            name='Customer',
            color='blue'
        )

    def test_tag_creation(self):
        """Test tag is created correctly."""
        self.assertEqual(self.tag.name, 'Customer')
        self.assertEqual(self.tag.color, 'blue')

    def test_tag_unique_name_per_organization(self):
        """Test name uniqueness constraint per organization."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Tag.objects.create(
                organization=self.organization,
                name='Customer'  # Duplicate name
            )

    def test_tag_str(self):
        """Test string representation."""
        self.assertEqual(str(self.tag), 'Customer')


class ContactTagModelTest(TestCase):
    """Tests for ContactTag model."""

    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
        self.contact = Contact.objects.create(
            organization=self.organization,
            email='contact@example.com'
        )
        self.tag = Tag.objects.create(
            organization=self.organization,
            name='Customer'
        )

    def test_contact_tag_creation(self):
        """Test ContactTag is created correctly."""
        contact_tag = ContactTag.objects.create(
            contact=self.contact,
            tag=self.tag
        )

        self.assertEqual(contact_tag.contact, self.contact)
        self.assertEqual(contact_tag.tag, self.tag)

    def test_contact_tag_unique_constraint(self):
        """Test unique constraint on contact-tag pair."""
        from django.db import IntegrityError

        ContactTag.objects.create(contact=self.contact, tag=self.tag)

        with self.assertRaises(IntegrityError):
            ContactTag.objects.create(
                contact=self.contact,
                tag=self.tag  # Duplicate
            )


class CustomFieldModelTest(TestCase):
    """Tests for CustomField model."""

    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )

    def test_custom_field_creation(self):
        """Test CustomField is created correctly."""
        field = CustomField.objects.create(
            organization=self.organization,
            name='Department',
            field_type='text',
            is_required=True
        )

        self.assertEqual(field.name, 'Department')
        self.assertEqual(field.field_type, 'text')
        self.assertTrue(field.is_required)

    def test_custom_field_dropdown(self):
        """Test CustomField with dropdown type."""
        field = CustomField.objects.create(
            organization=self.organization,
            name='Status',
            field_type='dropdown',
            dropdown_options=['New', 'Active', 'Inactive']
        )

        self.assertEqual(field.field_type, 'dropdown')
        self.assertEqual(len(field.dropdown_options), 3)
        self.assertIn('Active', field.dropdown_options)

    def test_custom_field_unique_name_per_organization(self):
        """Test name uniqueness constraint per organization."""
        from django.db import IntegrityError

        CustomField.objects.create(
            organization=self.organization,
            name='Department',
            field_type='text'
        )

        with self.assertRaises(IntegrityError):
            CustomField.objects.create(
                organization=self.organization,
                name='Department'  # Duplicate
            )
