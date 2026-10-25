"""
Custom field definitions, finally enforced.

The definitions and the values both existed from the start — `CustomField`, and
`Contact.custom_fields` — with nothing between them.
`ContactSerializer.validate_custom_fields` was documented as validating against
the definitions and only checked that the payload was a dictionary.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.contacts.custom_fields import CustomFieldError, CustomFieldService
from apps.contacts.models import Contact, CustomField


class DefinitionEnforcementTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        self.text = CustomField.objects.create(
            organization=self.org, name='Industry', field_type='text',
        )
        self.number = CustomField.objects.create(
            organization=self.org, name='Headcount', field_type='number',
        )
        self.dropdown = CustomField.objects.create(
            organization=self.org, name='Tier', field_type='dropdown',
            dropdown_options=['gold', 'silver'],
        )

    def _coerce(self, values, **kwargs):
        return CustomFieldService.validate_and_coerce(self.org, values, **kwargs)

    def test_an_undeclared_key_is_refused(self):
        """
        Refused rather than dropped. Silently discarding it is how a customer
        finds out months later that an integration has been writing to a field
        name nobody declared.
        """
        with self.assertRaises(CustomFieldError) as caught:
            self._coerce({'not_a_field': 'x'})

        self.assertIn('not_a_field', caught.exception.errors)

    def test_a_number_field_stores_a_number(self):
        cleaned = self._coerce({'headcount': '250'})

        self.assertEqual(cleaned['headcount'], 250)
        self.assertIsInstance(cleaned['headcount'], int)

    def test_a_number_field_refuses_text_and_names_itself(self):
        with self.assertRaises(CustomFieldError) as caught:
            self._coerce({'headcount': 'lots'})

        self.assertIn('Headcount', caught.exception.errors['headcount'])

    def test_a_dropdown_refuses_a_value_outside_its_options(self):
        with self.assertRaises(CustomFieldError) as caught:
            self._coerce({'tier': 'platinum'})

        self.assertIn('gold', caught.exception.errors['tier'])

    def test_a_dropdown_accepts_a_declared_option(self):
        self.assertEqual(self._coerce({'tier': 'gold'})['tier'], 'gold')

    def test_a_required_field_blocks_a_create(self):
        CustomField.objects.create(
            organization=self.org, name='Region', field_type='text', is_required=True,
        )

        with self.assertRaises(CustomFieldError) as caught:
            self._coerce({'industry': 'Mining'}, partial=False)

        self.assertIn('region', caught.exception.errors)

    def test_a_required_field_does_not_block_an_update_of_another_field(self):
        """
        An update that sets one field must not fail because a different
        required one was not in this payload.
        """
        CustomField.objects.create(
            organization=self.org, name='Region', field_type='text', is_required=True,
        )

        self.assertEqual(self._coerce({'industry': 'Mining'})['industry'], 'Mining')

    def test_a_multiselect_accepts_a_list_and_a_comma_separated_string(self):
        CustomField.objects.create(
            organization=self.org, name='Interests', field_type='multiselect',
            dropdown_options=['email', 'sms', 'post'],
        )

        self.assertEqual(self._coerce({'interests': ['email', 'sms']})['interests'],
                         ['email', 'sms'])
        # The form a CSV cell arrives in.
        self.assertEqual(self._coerce({'interests': 'email, post'})['interests'],
                         ['email', 'post'])

    def test_a_multiselect_refuses_an_undeclared_choice(self):
        CustomField.objects.create(
            organization=self.org, name='Interests', field_type='multiselect',
            dropdown_options=['email'],
        )

        with self.assertRaises(CustomFieldError):
            self._coerce({'interests': ['email', 'carrier_pigeon']})

    def test_a_url_field_refuses_something_that_is_not_a_url(self):
        CustomField.objects.create(
            organization=self.org, name='Blog', field_type='url',
        )

        with self.assertRaises(CustomFieldError):
            self._coerce({'blog': 'not a url'})

        self.assertEqual(
            self._coerce({'blog': 'https://example.com'})['blog'],
            'https://example.com',
        )

    def test_merging_keeps_the_values_it_was_not_given(self):
        """Replacement is what let a single-column CSV wipe everything else."""
        merged = CustomFieldService.merge(
            self.org, {'industry': 'Mining', 'tier': 'gold'}, {'industry': 'Retail'},
        )

        self.assertEqual(merged, {'industry': 'Retail', 'tier': 'gold'})

    def test_definitions_are_scoped_to_the_organization(self):
        other = Organization.objects.create(name='Theirs', slug='theirs')
        CustomField.objects.create(
            organization=other, name='Their Field', field_type='text',
        )

        with self.assertRaises(CustomFieldError):
            self._coerce({'their_field': 'x'})


class KeyAndLabelTests(TestCase):
    """
    The split that makes renaming safe.

    `name` used to be both the label and the JSON key, so renaming a field
    orphaned every value stored under the old name.
    """

    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')

    def test_a_key_is_derived_from_the_name(self):
        field = CustomField.objects.create(
            organization=self.org, name='Annual Revenue', field_type='number',
        )

        self.assertEqual(field.key, 'annual_revenue')

    def test_a_key_collision_is_resolved(self):
        CustomField.objects.create(organization=self.org, name='Annual Revenue')
        second = CustomField.objects.create(organization=self.org, name='Annual-Revenue')

        self.assertEqual(second.key, 'annual_revenue_1')

    def test_renaming_does_not_change_the_key(self):
        """The whole point: the stored data stays reachable."""
        field = CustomField.objects.create(organization=self.org, name='Industry')
        original_key = field.key

        field.name = 'Sector'
        field.save()
        field.refresh_from_db()

        self.assertEqual(field.key, original_key)

    def test_a_renamed_field_still_finds_its_data(self):
        field = CustomField.objects.create(organization=self.org, name='Industry')
        contact = Contact.objects.create(
            organization=self.org, email='a@example.com',
            custom_fields={field.key: 'Mining'},
        )

        field.name = 'Sector'
        field.save()

        cleaned = CustomFieldService.validate_and_coerce(
            self.org, contact.custom_fields,
        )
        self.assertEqual(cleaned[field.key], 'Mining')

    def test_the_api_will_not_let_the_key_be_changed(self):
        user = User.objects.create_user(
            email='me@mine.test', password='x', organization=self.org, role='owner',
        )
        api = APIClient()
        api.force_authenticate(user=user)
        field = CustomField.objects.create(organization=self.org, name='Industry')

        response = api.patch(
            f'/api/v1/custom-fields/{field.id}/',
            {'key': 'something_else', 'name': 'Sector'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        field.refresh_from_db()
        self.assertEqual(field.key, 'industry')
        self.assertEqual(field.name, 'Sector')


class ContactApiEnforcementTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        self.user = User.objects.create_user(
            email='me@mine.test', password='x', organization=self.org, role='owner',
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        CustomField.objects.create(
            organization=self.org, name='Headcount', field_type='number',
        )

    def test_creating_a_contact_coerces_its_custom_values(self):
        response = self.api.post(
            '/api/v1/contacts/',
            {'email': 'a@example.com', 'custom_fields': {'headcount': '250'}},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        contact = Contact.objects.get(email='a@example.com')
        self.assertEqual(contact.custom_fields['headcount'], 250)

    def test_creating_a_contact_with_an_undeclared_field_is_a_400(self):
        response = self.api.post(
            '/api/v1/contacts/',
            {'email': 'a@example.com', 'custom_fields': {'nope': 'x'}},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('nope', str(response.data))

    def test_the_error_is_reported_against_the_offending_key(self):
        response = self.api.post(
            '/api/v1/contacts/',
            {'email': 'a@example.com', 'custom_fields': {'headcount': 'lots'}},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('headcount', str(response.data))


class SegmentIntegrationTests(TestCase):
    """
    Custom fields in the rule builder.

    They could not be offered at all before: the field list was a module-level
    dict with no organization in scope, so a customer had to know to hand-write
    `custom.industry`, and then got string operators for it whatever its type.
    """

    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        CustomField.objects.create(
            organization=self.org, name='Headcount', field_type='number',
        )

    def test_the_builders_field_list_includes_custom_fields(self):
        from apps.segments.evaluator import SegmentEvaluator

        definitions = SegmentEvaluator.get_field_definitions(self.org)

        self.assertIn('custom.headcount', definitions)
        self.assertEqual(definitions['custom.headcount']['type'], 'number')
        self.assertTrue(definitions['custom.headcount']['custom'])

    def test_a_number_custom_field_gets_number_operators(self):
        from apps.segments.evaluator import SegmentEvaluator

        operators = dict(SegmentEvaluator.get_operators_for_field(
            'custom.headcount', organization=self.org,
        ))

        self.assertIn('greater_than', operators)

    def test_a_custom_field_is_not_visible_to_another_organization(self):
        from apps.segments.evaluator import SegmentEvaluator

        other = Organization.objects.create(name='Theirs', slug='theirs')

        self.assertNotIn(
            'custom.headcount', SegmentEvaluator.get_field_definitions(other),
        )


class KeyBackfillMigrationTests(TestCase):
    """
    The migration that gives existing definitions a key and moves their data.

    Before `key` existed, `name` was the JSON key by convention. Backfilling
    `key = slugify(name)` without touching the data would orphan every value a
    customer holds: the definition would say `industry_type` while the contact
    held `"Industry Type"`.
    """

    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        self.other = Organization.objects.create(name='Theirs', slug='theirs')

    def _field(self, organization, name):
        """
        A definition as it looked before the key column existed.

        Inserted through the queryset rather than create(), because save()
        derives a key and the point here is a row that has none. Written one
        at a time with a unique placeholder key: the real pre-migration state
        had no key column at all, and the column is unique now, so two blanks
        cannot coexist in a test database that already has the constraint.
        """
        field = CustomField.objects.create(organization=organization, name=name)
        # A placeholder the backfill will treat as absent.
        CustomField.objects.filter(pk=field.pk).update(key='')
        field.refresh_from_db()
        return field

    def _run(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        module = import_module(
            'apps.contacts.migrations.0007_backfill_custom_field_keys'
        )
        module.derive_keys(django_apps, None)

    def test_a_key_is_derived_for_a_definition_that_has_none(self):
        self._field(self.org, 'Industry Type')

        self._run()

        self.assertEqual(
            CustomField.objects.get(organization=self.org).key, 'industry_type',
        )

    def test_the_stored_values_move_to_the_new_key(self):
        """The half that would otherwise orphan the data."""
        self._field(self.org, 'Industry Type')
        contact = Contact.objects.create(
            organization=self.org, email='a@example.com',
            custom_fields={'Industry Type': 'Mining', 'untouched': 'keep me'},
        )

        self._run()

        contact.refresh_from_db()
        self.assertEqual(contact.custom_fields['industry_type'], 'Mining')
        self.assertNotIn('Industry Type', contact.custom_fields)
        # Keys matching no definition are left alone rather than guessed at or
        # deleted — the old code validated nothing, so they may exist.
        self.assertEqual(contact.custom_fields['untouched'], 'keep me')

    def test_a_value_already_under_the_new_key_is_not_overwritten(self):
        self._field(self.org, 'Industry Type')
        contact = Contact.objects.create(
            organization=self.org, email='a@example.com',
            custom_fields={'Industry Type': 'old', 'industry_type': 'current'},
        )

        self._run()

        contact.refresh_from_db()
        self.assertEqual(contact.custom_fields['industry_type'], 'current')

    def test_the_key_constraint_is_applied_after_the_backfill(self):
        """
        The ordering bug this file found.

        The unique constraint on (organization, key) was originally added in
        the same migration as the column, so it was checked while every
        pre-existing row still had a blank key — two definitions in one
        organization made the migration fail outright. It now lives in 0009,
        after 0007 derives the keys.

        Read from the migration files rather than Django's loader, because the
        fast test settings disable migrations and the loader would see none.
        The forward run itself was verified by hand against a seeded pre-key
        database.
        """
        from pathlib import Path

        directory = Path(__file__).resolve().parent.parent / 'migrations'

        backfill = None
        constraint = None
        for path in sorted(directory.glob('0*.py')):
            source = path.read_text(encoding='utf-8')
            if 'derive_keys' in source and 'RunPython' in source:
                backfill = path.name
            if "unique_together={('organization', 'key')" in source \
                    or '("organization", "key")' in source:
                constraint = path.name

        self.assertIsNotNone(backfill, 'no migration derives the custom field keys')
        self.assertIsNotNone(
            constraint, 'no migration adds the (organization, key) constraint',
        )
        # Migration file names sort in application order.
        self.assertLess(
            backfill, constraint,
            f'{constraint} adds the key constraint before {backfill} derives the keys',
        )
    def test_one_organizations_rename_does_not_touch_another(self):
        self._field(self.org, 'Industry Type')
        theirs = Contact.objects.create(
            organization=self.other, email='b@example.com',
            custom_fields={'Industry Type': 'theirs'},
        )

        self._run()

        theirs.refresh_from_db()
        # Their organization has no such definition, so nothing is renamed for
        # them — a rename is derived per organization, not globally.
        self.assertEqual(theirs.custom_fields, {'Industry Type': 'theirs'})

    def test_a_definition_that_already_has_a_key_is_left_alone(self):
        field = CustomField.objects.create(
            organization=self.org, name='Industry', key='legacy_key',
        )

        self._run()

        field.refresh_from_db()
        self.assertEqual(field.key, 'legacy_key')
