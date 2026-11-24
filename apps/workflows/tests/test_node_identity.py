"""
A node keeps its identity across a save.

Saving a workflow used to delete every node and create them again with fresh
UUIDs. Three things point at a node, and all three broke every time somebody
moved a box on the canvas:

  * `WorkflowExecutionStep.node` (SET_NULL) — every past run became a list of
    "Unknown step / Deleted Node", which is how this was noticed;
  * `WorkflowSegmentWatch.node` (CASCADE) — the watches were simply gone;
  * `WorkflowExecution.current_node` (SET_NULL) — where a contact waiting in a
    Wait step keeps its place. Resuming one with no current node does nothing,
    so the contact stayed "active" forever and the run never finished.
"""
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.contacts.models import Contact
from apps.workflows.models import (
    Workflow, WorkflowEdge, WorkflowExecution, WorkflowExecutionStep,
    WorkflowNode,
)


class NodeIdentityTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.workflow = Workflow.objects.create(
            organization=self.org, name='Welcome', status='active',
        )
        self.trigger = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.TRIGGER_CONTACT_CREATED,
            label='New contact', position_x=0, position_y=0,
        )
        self.wait = WorkflowNode.objects.create(
            workflow=self.workflow, node_type='action_wait',
            label='Wait 2 days', position_x=0, position_y=150,
            config={'days': 2},
        )
        WorkflowEdge.objects.create(
            workflow=self.workflow, source_node=self.trigger,
            target_node=self.wait,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def save_canvas(self, nodes, edges=None):
        """Save as the builder does: existing nodes carry their own UUIDs."""
        response = self.client.patch(
            f'/api/v1/workflows/{self.workflow.id}/',
            {'nodes': nodes, 'edges': edges if edges is not None else []},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        return response

    def canvas(self, **overrides):
        """The two nodes as they stand, ready to send back."""
        nodes = [
            {
                'id': str(self.trigger.id),
                'node_type': self.trigger.node_type,
                'label': self.trigger.label,
                'position_x': 0, 'position_y': 0, 'config': {},
            },
            {
                'id': str(self.wait.id),
                'node_type': self.wait.node_type,
                'label': self.wait.label,
                'position_x': 0, 'position_y': 150, 'config': {'days': 2},
            },
        ]
        nodes[1].update(overrides)
        return nodes


class IdentitySurvivesSaveTests(NodeIdentityTestCase):
    def test_the_ids_are_the_same_afterwards(self):
        before = {str(n.id) for n in self.workflow.nodes.all()}

        self.save_canvas(self.canvas(position_x=400))

        after = {str(n.id) for n in self.workflow.nodes.all()}
        self.assertEqual(before, after)

    def test_a_move_is_stored(self):
        self.save_canvas(self.canvas(position_x=400, position_y=999))

        self.wait.refresh_from_db()
        self.assertEqual(self.wait.position_x, 400)
        self.assertEqual(self.wait.position_y, 999)

    def test_a_past_run_still_knows_which_step_it_took(self):
        contact = Contact.objects.create(
            organization=self.org, email='ada@example.com'
        )
        execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=contact, status='completed',
        )
        step = WorkflowExecutionStep.objects.create(
            execution=execution, node=self.wait, status='completed',
        )

        self.save_canvas(self.canvas(position_x=400))

        step.refresh_from_db()
        self.assertIsNotNone(step.node, 'the step lost the node it ran')
        self.assertEqual(step.node_id, self.wait.id)

    def test_a_waiting_contact_keeps_its_place(self):
        """
        The one that strands people: resume does nothing without a current
        node, so the run would sit "active" and never move again.
        """
        contact = Contact.objects.create(
            organization=self.org, email='ada@example.com'
        )
        execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=contact, status='waiting',
            current_node=self.wait, resume_at=timezone.now(),
        )

        self.save_canvas(self.canvas(position_x=400))

        execution.refresh_from_db()
        self.assertEqual(execution.current_node_id, self.wait.id)

    def test_the_connections_are_not_doubled(self):
        self.save_canvas(
            self.canvas(),
            edges=[{
                'source': str(self.trigger.id),
                'target': str(self.wait.id),
                'sourceHandle': 'default',
                'targetHandle': 'default',
            }],
        )

        self.assertEqual(self.workflow.edges.count(), 1)


class CanvasChangesTests(NodeIdentityTestCase):
    def test_a_new_step_is_created(self):
        nodes = self.canvas() + [{
            'id': 'reactflow__node-3',
            'node_type': WorkflowNode.ACTION_ADD_TAG,
            'label': 'Tag them', 'position_x': 0, 'position_y': 300,
            'config': {},
        }]

        self.save_canvas(nodes)

        self.assertEqual(self.workflow.nodes.count(), 3)
        self.assertTrue(
            self.workflow.nodes.filter(label='Tag them').exists()
        )

    def test_a_removed_step_is_deleted(self):
        self.save_canvas([self.canvas()[0]])

        self.assertEqual(self.workflow.nodes.count(), 1)
        self.assertFalse(
            WorkflowNode.objects.filter(pk=self.wait.pk).exists()
        )

    def test_a_different_type_under_the_same_id_replaces_the_step(self):
        """
        Keeping the id would relabel the history of every run that went
        through the old step.
        """
        old_id = self.wait.id

        self.save_canvas(self.canvas(
            node_type=WorkflowNode.ACTION_ADD_TAG, label='Tag instead',
        ))

        self.assertFalse(WorkflowNode.objects.filter(pk=old_id).exists())
        self.assertTrue(
            self.workflow.nodes.filter(label='Tag instead').exists()
        )
        self.assertEqual(self.workflow.nodes.count(), 2)
