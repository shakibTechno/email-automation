"""
Starting a workflow from a template.

This is the "Create Workflow" button — the way almost everyone meets the
feature. It used to have its own copy of the node-building code; it now goes
through the same builder as import and AI generation, which validates node
types and re-points references. That reroute is what these tests cover: a
template that silently produced an empty workflow would be the worst possible
first impression.
"""
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import Organization, User
from apps.workflows import catalog
from apps.workflows.models import Workflow, WorkflowTemplate
from apps.workflows.services import WorkflowService


class SystemTemplateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('create_workflow_templates', verbosity=0)

    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )

    def test_the_shipped_templates_exist(self):
        self.assertGreater(WorkflowTemplate.objects.count(), 0)

    def test_every_template_only_uses_steps_that_exist(self):
        """
        A template naming a node type the catalogue does not have would lose
        that step on creation, giving a workflow that looks finished and does
        something else.
        """
        for template in WorkflowTemplate.objects.all():
            for node in (template.template_data or {}).get('nodes', []):
                with self.subTest(f'{template.name}: {node.get("node_type")}'):
                    self.assertTrue(catalog.exists(node.get('node_type')))

    def test_every_template_has_a_trigger(self):
        for template in WorkflowTemplate.objects.all():
            with self.subTest(template.name):
                types = {
                    node.get('node_type')
                    for node in (template.template_data or {}).get('nodes', [])
                }
                self.assertTrue(
                    types & catalog.TRIGGER_TYPES,
                    f'"{template.name}" would create a workflow nothing starts',
                )

    def test_each_template_creates_a_workflow_with_all_its_steps(self):
        for template in WorkflowTemplate.objects.all():
            with self.subTest(template.name):
                expected_nodes = len(
                    (template.template_data or {}).get('nodes', [])
                )
                expected_edges = len(
                    (template.template_data or {}).get('edges', [])
                )

                workflow = WorkflowService.create_from_template(
                    template, self.org, user=self.user,
                )

                self.assertEqual(workflow.nodes.count(), expected_nodes)
                self.assertEqual(workflow.edges.count(), expected_edges)

    def test_a_template_workflow_belongs_to_the_account_that_made_it(self):
        template = WorkflowTemplate.objects.first()
        workflow = WorkflowService.create_from_template(
            template, self.org, user=self.user,
        )

        self.assertEqual(workflow.organization, self.org)
        self.assertEqual(workflow.created_by, self.user)
        for node in workflow.nodes.all():
            self.assertEqual(node.workflow_id, workflow.id)

    def test_it_arrives_as_a_draft(self):
        template = WorkflowTemplate.objects.first()
        workflow = WorkflowService.create_from_template(template, self.org)
        self.assertEqual(workflow.status, 'draft')

    def test_the_branches_of_a_condition_survive(self):
        """
        A template's true/false edges are the whole point of the template that
        has them; dropping one leaves a dead branch.
        """
        for template in WorkflowTemplate.objects.all():
            edges = (template.template_data or {}).get('edges', [])
            branches = {
                edge.get('edge_type') for edge in edges
            } - {'default', None}
            if not branches:
                continue

            with self.subTest(template.name):
                workflow = WorkflowService.create_from_template(template, self.org)
                self.assertEqual(
                    {
                        edge.edge_type for edge in workflow.edges.all()
                    } - {'default'},
                    branches,
                )

    def test_using_a_template_counts_it(self):
        template = WorkflowTemplate.objects.first()
        before = template.usage_count

        WorkflowService.create_from_template(template, self.org)

        template.refresh_from_db()
        self.assertEqual(template.usage_count, before + 1)

    def test_two_accounts_can_use_the_same_template(self):
        other = Organization.objects.create(name='Other Ltd', slug='other')
        template = WorkflowTemplate.objects.first()

        mine = WorkflowService.create_from_template(template, self.org)
        theirs = WorkflowService.create_from_template(template, other)

        self.assertNotEqual(mine.id, theirs.id)
        self.assertEqual(theirs.organization, other)
        # No node of one account's workflow may point at the other's.
        self.assertFalse(
            Workflow.objects.filter(
                id=mine.id, nodes__workflow__organization=other
            ).exists()
        )

    def test_seeding_twice_does_not_duplicate_the_templates(self):
        before = WorkflowTemplate.objects.count()
        call_command('create_workflow_templates', verbosity=0)
        self.assertEqual(WorkflowTemplate.objects.count(), before)
