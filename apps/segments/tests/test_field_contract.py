"""
Which fields a segment rule may name.

`FIELD_DEFINITIONS` was a hand-maintained copy of the contact's shape and had
already drifted: it advertised a "Status" field the Contact model has never
had, so a rule built on it produced `Q(status__iexact=...)` and raised
`FieldError` — a 500 on preview and on every later use of that segment.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.contacts import fields as contact_fields
from apps.contacts.models import Contact
from apps.segments.evaluator import (
    FIELD_DEFINITIONS,
    SegmentEvaluator,
    UnknownSegmentField,
    operator_type,
)
from apps.segments.services import SegmentService


class FieldDefinitionContractTests(TestCase):
    def test_no_field_is_offered_that_the_model_does_not_have(self):
        """The drift that caused the 500, asserted away."""
        model_names = {f.name for f in Contact._meta.get_fields()}
        model_names |= {
            f.attname for f in Contact._meta.get_fields() if hasattr(f, 'attname')
        }
        special = {'tag'}  # not a column; has its own evaluation branch

        offered = set(FIELD_DEFINITIONS) - special

        self.assertEqual(sorted(offered - model_names), [])

    def test_status_is_offered_and_now_actually_exists(self):
        """
        The field the builder always advertised. It was a phantom until the
        column was added; this asserts the pairing rather than either half, so
        offering it again without the column fails here.
        """
        self.assertIn('status', FIELD_DEFINITIONS)
        Contact.objects.filter(status='active').exists()

    def test_the_offered_list_is_the_registrys_segmentable_set(self):
        self.assertEqual(
            set(FIELD_DEFINITIONS) - {'tag'},
            set(contact_fields.segmentable_specs()),
        )

    def test_every_offered_field_has_usable_operators(self):
        for key in FIELD_DEFINITIONS:
            with self.subTest(field=key):
                self.assertTrue(SegmentEvaluator.get_operators_for_field(key))


class UnknownFieldTests(TestCase):
    """
    A rule naming a field that does not exist is a bad request, not a 500.

    It still matters after the drift is fixed: segments built on the phantom
    "Status" field are already stored in customers' databases.
    """

    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        Contact.objects.create(organization=self.org, email='a@example.com')

    def _rules(self, field):
        return {
            'match': 'all',
            'conditions': [{'field': field, 'operator': 'equals', 'value': 'x'}],
        }

    def test_building_a_query_on_an_unknown_field_raises_our_own_error(self):
        with self.assertRaises(UnknownSegmentField):
            SegmentEvaluator.build_query(self._rules('no_such_field'))

    def test_the_error_names_the_field(self):
        with self.assertRaises(UnknownSegmentField) as caught:
            SegmentEvaluator.build_query(self._rules('nonsense'))

        self.assertIn('nonsense', str(caught.exception))

    def test_previewing_such_a_segment_is_a_400_not_a_500(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            SegmentService.preview_rules(self.org, self._rules('no_such_field'))

    def test_validation_rejects_an_unknown_field_at_save_time(self):
        errors = SegmentService.validate_rules(self._rules('no_such_field'))

        self.assertTrue(errors)
        self.assertIn('no_such_field', ' '.join(errors))


class StatusSegmentTests(TestCase):
    """
    The bug that started this, closed properly.

    A rule on "Status" used to raise FieldError because the column did not
    exist. It does now, and it is derived from the subscription flags rather
    than maintained beside them.
    """

    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        self.active = Contact.objects.create(
            organization=self.org, email='active@example.com',
        )
        self.gone = Contact.objects.create(
            organization=self.org, email='gone@example.com',
        )
        self.gone.unsubscribe()

    def test_a_rule_on_status_returns_the_right_contacts(self):
        query = SegmentEvaluator.build_query({
            'match': 'all',
            'conditions': [
                {'field': 'status', 'operator': 'equals', 'value': 'unsubscribed'},
            ],
        })

        matched = Contact.objects.filter(organization=self.org).filter(query)

        self.assertEqual([c.email for c in matched], ['gone@example.com'])

    def test_status_follows_the_flags_without_being_set(self):
        self.assertEqual(self.active.status, 'active')
        self.gone.refresh_from_db()
        self.assertEqual(self.gone.status, 'unsubscribed')

        self.gone.resubscribe()
        self.gone.refresh_from_db()
        self.assertEqual(self.gone.status, 'active')

    def test_a_complaint_outranks_an_unsubscribe(self):
        self.gone.mark_complained()
        self.gone.refresh_from_db()

        self.assertEqual(self.gone.status, 'complained')

    def test_a_bounce_outranks_an_unsubscribe(self):
        self.gone.mark_bounced('hard')
        self.gone.refresh_from_db()

        self.assertEqual(self.gone.status, 'bounced')
        self.assertEqual(self.gone.bounce_type, 'hard')


class TypeDispatchTests(TestCase):
    """
    Conditions dispatch on the declared type, not on hardcoded name lists.

    The old lists had to be extended for every new field and silently treated
    anything they missed as a string — which would have compared a date
    alphabetically.
    """

    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        self.low = Contact.objects.create(
            organization=self.org, email='low@example.com', lead_score=5,
        )
        self.high = Contact.objects.create(
            organization=self.org, email='high@example.com', lead_score=90,
        )

    def test_a_number_field_compares_numerically(self):
        query = SegmentEvaluator.build_query({
            'match': 'all',
            'conditions': [
                {'field': 'lead_score', 'operator': 'greater_than', 'value': 50},
            ],
        })

        matched = Contact.objects.filter(organization=self.org).filter(query)

        self.assertEqual([c.email for c in matched], ['high@example.com'])

    def test_a_datetime_field_gets_date_operators(self):
        """
        The registry calls these `datetime`; the operator table only knows
        `date`. One map between the two vocabularies, so a timestamp does not
        fall through to string operators.
        """
        self.assertEqual(operator_type('datetime'), 'date')

        operators = dict(SegmentEvaluator.get_operators_for_field('created_at'))

        self.assertIn('in_last_days', operators)

    def test_an_email_field_gets_string_operators(self):
        operators = dict(SegmentEvaluator.get_operators_for_field('email'))

        self.assertIn('contains', operators)
