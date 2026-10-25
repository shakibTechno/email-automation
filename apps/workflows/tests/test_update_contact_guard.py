"""
What the "update contact" workflow action may write.

Every branch of this handler used to `setattr` whatever name the node config
carried — `set` behind a `hasattr` check, and increment, decrement and append
behind nothing at all. A node configured with `field: "organization_id"`
therefore moved the contact into another tenant's organization.
"""
from django.test import TestCase

from apps.accounts.models import Organization, User
from apps.contacts.models import Contact
from apps.workflows.models import Workflow, WorkflowExecution, WorkflowNode
from apps.workflows.services import WorkflowExecutionService


class UpdateContactGuardTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        self.other = Organization.objects.create(name='Theirs', slug='theirs')
        self.user = User.objects.create_user(
            email='me@mine.test', password='x', organization=self.org, role='owner',
        )
        self.contact = Contact.objects.create(
            organization=self.org, email='c@example.com', company='Acme', lead_score=10,
        )
        self.workflow = Workflow.objects.create(
            organization=self.org, name='W', created_by=self.user,
        )
        self.execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=self.contact,
        )

    def _node(self, **config):
        return WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.ACTION_UPDATE_CONTACT,
            config=config,
        )

    def _run(self, **config):
        return WorkflowExecutionService._handle_update_contact(
            self.execution, self._node(**config),
        )

    # ------------------------------------------------------------ the hole
    def test_the_organization_cannot_be_written(self):
        with self.assertRaises(ValueError):
            self._run(field='organization_id', value=str(self.other.id), operation='set')

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.organization, self.org)

    def test_protected_internals_cannot_be_written(self):
        for field in ('id', 'deleted_at', 'custom_fields', 'assigned_to_id'):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self._run(field=field, value='x', operation='set')

    def test_the_scoring_engines_fields_cannot_be_written(self):
        """lead_score belongs to the scoring engine, not to a workflow node."""
        with self.assertRaises(ValueError):
            self._run(field='lead_score', value='999', operation='set')

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.lead_score, 10)

    def test_increment_was_unguarded_and_now_is_not(self):
        """`increment` had no hasattr check at all, let alone a whitelist."""
        with self.assertRaises(ValueError):
            self._run(field='lead_score', value='5', operation='increment')

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.lead_score, 10)

    def test_append_was_unguarded_and_now_is_not(self):
        with self.assertRaises(ValueError):
            self._run(field='organization_id', value='x', operation='append')

    # ------------------------------------------------- what still works
    def test_a_writable_column_is_set(self):
        self._run(field='company', value='Globex', operation='set')

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.company, 'Globex')

    def test_an_unknown_name_is_treated_as_a_custom_field(self):
        """Preserves the previous behaviour, and it is safe: JSON, not a column."""
        self._run(field='industry', value='Mining', operation='set')

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.custom_fields['industry'], 'Mining')

    def test_an_explicit_custom_target_also_works(self):
        self._run(field='custom.tier', value='gold', operation='set')

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.custom_fields['tier'], 'gold')

    def test_a_custom_field_can_be_incremented(self):
        self.contact.custom_fields = {'visits': 2}
        self.contact.save()

        self._run(field='visits', value='3', operation='increment')

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.custom_fields['visits'], 5)

    def test_incrementing_a_text_column_is_refused_rather_than_concatenated(self):
        """`company` + 1 used to produce "Acme1"."""
        with self.assertRaises(ValueError):
            self._run(field='company', value='1', operation='increment')

    def test_setting_a_custom_field_keeps_the_others(self):
        self.contact.custom_fields = {'tier': 'gold'}
        self.contact.save()

        self._run(field='industry', value='Mining', operation='set')

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.custom_fields['tier'], 'gold')
        self.assertEqual(self.contact.custom_fields['industry'], 'Mining')

    def test_an_unknown_operation_is_refused(self):
        with self.assertRaises(ValueError):
            self._run(field='company', value='x', operation='obliterate')
