"""A CSV saved by Excel carries a byte order mark."""
import io

from django.test import TestCase

from apps.accounts.models import Organization, User
from apps.contacts.models import Contact
from apps.contacts.services import CSVImportService


class BomCsvImportTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )

    def test_a_csv_with_a_byte_order_mark_still_finds_the_email_column(self):
        """
        Decoded as plain utf-8 the BOM stays glued to the first header, so
        `email` mapped to nothing and every row was skipped for having none.
        """
        csv_bytes = io.BytesIO(
            'email,company\nada@example.com,Acme\n'.encode('utf-8-sig')
        )

        result = CSVImportService(self.org, self.user).import_from_csv(csv_bytes)

        self.assertEqual(result['imported'], 1, result.get('errors'))
        self.assertTrue(
            Contact.objects.filter(organization=self.org, email='ada@example.com')
            .exists()
        )
