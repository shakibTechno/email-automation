"""
Tests for Contact views and API endpoints.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import Organization, User
from apps.contacts.models import Contact, Tag, ContactTag, CustomField
import io


class ContactViewSetTest(TestCase):
    """Tests for ContactViewSet."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            organization=self.organization,
            first_name='Test',
            last_name='User'
        )
        self.client.force_authenticate(user=self.user)

        # Create test contacts
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

    def test_list_contacts(self):
        """Test listing contacts."""
        url = reverse('contacts:contact-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_create_contact(self):
        """Test creating a contact."""
        url = reverse('contacts:contact-list')
        data = {
            'email': 'newcontact@example.com',
            'first_name': 'New',
            'last_name': 'Contact',
            'company': 'New Company'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Contact.objects.count(), 3)
        self.assertEqual(
            Contact.objects.get(email='newcontact@example.com').first_name,
            'New'
        )

    def test_create_duplicate_contact(self):
        """Test creating a contact with duplicate email."""
        url = reverse('contacts:contact-list')
        data = {
            'email': 'contact1@example.com',  # Duplicate
            'first_name': 'Duplicate',
            'last_name': 'Contact'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_contact(self):
        """Test retrieving a contact."""
        url = reverse('contacts:contact-detail', args=[self.contact1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'contact1@example.com')
        self.assertEqual(response.data['first_name'], 'John')

    def test_update_contact(self):
        """Test updating a contact."""
        url = reverse('contacts:contact-detail', args=[self.contact1.id])
        data = {
            'email': 'contact1@example.com',
            'first_name': 'Updated',
            'last_name': 'Name',
            'company': 'Updated Company'
        }
        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.contact1.refresh_from_db()
        self.assertEqual(self.contact1.first_name, 'Updated')
        self.assertEqual(self.contact1.company, 'Updated Company')

    def test_delete_contact(self):
        """Test soft deleting a contact."""
        url = reverse('contacts:contact-detail', args=[self.contact1.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Contact.objects.count(), 1)  # Soft deleted
        self.assertEqual(Contact.all_objects.count(), 2)

    def test_search_contacts(self):
        """Test searching contacts."""
        url = reverse('contacts:contact-list')
        response = self.client.get(url, {'search': 'John'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['first_name'], 'John')

    def test_filter_contacts_by_company(self):
        """Test filtering contacts by company."""
        url = reverse('contacts:contact-list')
        response = self.client.get(url, {'company': 'Company A'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_bulk_delete_contacts(self):
        """Test bulk deleting contacts."""
        url = reverse('contacts:contact-bulk-delete')
        data = {
            'contact_ids': [str(self.contact1.id), str(self.contact2.id)]
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Contact.objects.count(), 0)

    def test_export_contacts(self):
        """Test exporting contacts to CSV."""
        url = reverse('contacts:contact-export')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])


class TagViewSetTest(TestCase):
    """Tests for TagViewSet."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            organization=self.organization
        )
        self.client.force_authenticate(user=self.user)

        self.tag = Tag.objects.create(
            organization=self.organization,
            name='Customer',
            color='blue'
        )

    def test_list_tags(self):
        """Test listing tags."""
        url = reverse('contacts:tag-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_tag(self):
        """Test creating a tag."""
        url = reverse('contacts:tag-list')
        data = {
            'name': 'VIP',
            'color': 'purple',
            'description': 'VIP customers'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tag.objects.count(), 2)

    def test_update_tag(self):
        """Test updating a tag."""
        url = reverse('contacts:tag-detail', args=[self.tag.id])
        data = {
            'name': 'Premium Customer',
            'color': 'gold'
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, 'Premium Customer')

    def test_delete_tag(self):
        """Test deleting a tag."""
        url = reverse('contacts:tag-detail', args=[self.tag.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Tag.objects.count(), 0)


class BulkOperationsTest(TestCase):
    """Tests for bulk operations."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            organization=self.organization
        )
        self.client.force_authenticate(user=self.user)

        self.contact1 = Contact.objects.create(
            organization=self.organization,
            email='contact1@example.com'
        )
        self.contact2 = Contact.objects.create(
            organization=self.organization,
            email='contact2@example.com'
        )
        self.tag1 = Tag.objects.create(
            organization=self.organization,
            name='Tag1'
        )
        self.tag2 = Tag.objects.create(
            organization=self.organization,
            name='Tag2'
        )

    def test_bulk_tag_add(self):
        """Test bulk adding tags to contacts."""
        url = reverse('contacts:contact-bulk-tag')
        data = {
            'contact_ids': [str(self.contact1.id), str(self.contact2.id)],
            'tag_ids': [str(self.tag1.id)],
            'action': 'add'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ContactTag.objects.count(), 2)

    def test_bulk_tag_remove(self):
        """Test bulk removing tags from contacts."""
        # First add tags
        ContactTag.objects.create(contact=self.contact1, tag=self.tag1)
        ContactTag.objects.create(contact=self.contact2, tag=self.tag1)

        url = reverse('contacts:contact-bulk-tag')
        data = {
            'contact_ids': [str(self.contact1.id), str(self.contact2.id)],
            'tag_ids': [str(self.tag1.id)],
            'action': 'remove'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ContactTag.objects.count(), 0)


class CustomFieldViewSetTest(TestCase):
    """Tests for CustomFieldViewSet."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            organization=self.organization
        )
        self.client.force_authenticate(user=self.user)

    def test_create_custom_field(self):
        """Test creating a custom field."""
        url = reverse('contacts:customfield-list')
        data = {
            'name': 'Department',
            'field_type': 'text',
            'is_required': False
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomField.objects.count(), 1)

    def test_create_dropdown_field(self):
        """Test creating a dropdown custom field."""
        url = reverse('contacts:customfield-list')
        data = {
            'name': 'Status',
            'field_type': 'dropdown',
            'dropdown_options': ['New', 'Active', 'Inactive']
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        field = CustomField.objects.first()
        self.assertEqual(len(field.dropdown_options), 3)
