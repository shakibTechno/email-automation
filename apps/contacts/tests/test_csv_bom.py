"""A CSV saved by Excel carries a byte order mark."""
import io
from unittest.mock import patch

from django.db import DatabaseError, transaction
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


class PartialImportTests(TestCase):
    """One unusable row must not discard the rest of the file."""

    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )

    def test_a_row_the_database_rejects_does_not_take_the_others_with_it(self):
        """
        A database error -- a phone number longer than its varchar(20) column,
        which is what happened on a real import -- marks the transaction for
        rollback. With one transaction around the whole loop that left the
        connection unusable, so every row after the bad one failed too, while
        the result still listed them individually as though it had recovered.

        Simulated rather than provoked: SQLite does not enforce varchar length,
        so the real error only appears on Postgres. mark_for_rollback_on_error
        is what Django itself does when a query fails, which is the part that
        actually broke the loop.
        """
        real_create = Contact.objects.create

        def create(**kwargs):
            if kwargs.get('email') == 'toolong@example.com':
                with transaction.mark_for_rollback_on_error():
                    raise DatabaseError('value too long for type character varying(20)')
            return real_create(**kwargs)

        csv_bytes = io.BytesIO((
            'email,phone\n'
            'first@example.com,+353 1 234 5678\n'
            'toolong@example.com,1800 201 765 / +353 (0)57 875 6700\n'
            'after@example.com,+353 1 999 0000\n'
        ).encode('utf-8'))

        with patch.object(Contact.objects, 'create', side_effect=create):
            result = CSVImportService(self.org, self.user).import_from_csv(csv_bytes)

        emails = set(
            Contact.objects.filter(organization=self.org)
            .values_list('email', flat=True)
        )
        self.assertIn('first@example.com', emails)
        self.assertIn('after@example.com', emails, 'the row after the bad one')
        self.assertNotIn('toolong@example.com', emails)
        self.assertEqual(result['imported'], 2)
        self.assertEqual(len(result['errors']), 1)
