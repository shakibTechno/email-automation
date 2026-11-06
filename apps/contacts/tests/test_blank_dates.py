"""
An empty string from a form means "no value", not a bad value.

An HTML date input that was never filled in sends `''`. DRF's DateField
rejects that outright, so editing *any* contact without a date of birth
failed with "Date has wrong format" and clearing a date was impossible.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, User
from apps.contacts.models import Contact


class BlankDateTestCase(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.contact = Contact.objects.create(
            organization=self.org, email='ada@example.com', first_name='Ada',
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('contacts:contact-detail', args=[self.contact.id])

    def test_editing_a_contact_with_no_birthday_succeeds(self):
        """The whole bug: the form round-trips '' for every empty field."""
        response = self.client.patch(
            self.url, {'first_name': 'Ada L', 'date_of_birth': ''}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.first_name, 'Ada L')
        self.assertIsNone(self.contact.date_of_birth)

    def test_a_date_already_set_can_be_cleared(self):
        self.contact.date_of_birth = '1990-05-04'
        self.contact.save(update_fields=['date_of_birth'])

        response = self.client.patch(
            self.url, {'date_of_birth': ''}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.contact.refresh_from_db()
        self.assertIsNone(self.contact.date_of_birth)

    def test_a_real_date_still_saves(self):
        response = self.client.patch(
            self.url, {'date_of_birth': '1990-05-04'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.contact.refresh_from_db()
        self.assertEqual(str(self.contact.date_of_birth), '1990-05-04')

    def test_a_genuinely_malformed_date_is_still_refused(self):
        """Blanking '' must not turn into accepting anything."""
        response = self.client.patch(
            self.url, {'date_of_birth': '04/05/1990'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_birth', response.data['details'])

    def test_a_blank_datetime_is_cleared_too(self):
        response = self.client.patch(
            self.url, {'consent_at': ''}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.contact.refresh_from_db()
        self.assertIsNone(self.contact.consent_at)

    def test_an_empty_text_field_stays_an_empty_string(self):
        """'' is a real value for text — it must not become NULL."""
        self.contact.company = 'Acme'
        self.contact.save(update_fields=['company'])

        response = self.client.patch(self.url, {'company': ''}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.company, '')

    def test_creating_a_contact_with_a_blank_date_works_the_same_way(self):
        """The create path is a different serializer; both share the mixin."""
        response = self.client.post(
            reverse('contacts:contact-list'),
            {'email': 'grace@example.com', 'date_of_birth': ''}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        created = Contact.objects.get(organization=self.org, email='grace@example.com')
        self.assertIsNone(created.date_of_birth)
