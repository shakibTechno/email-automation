"""
Removing a connection between two steps.

Deleting a connection is the one save that changes edges and not nodes, and
that was the case the update path dropped on the floor: the edge write sat
nested inside `if nodes_data is not None`, so a payload carrying edges alone
was accepted, reported success, and changed nothing.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, User
from apps.workflows.models import Workflow, WorkflowEdge, WorkflowNode


class EdgeEditingTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.client.force_authenticate(user=self.user)

        self.workflow = Workflow.objects.create(
            organization=self.org, name='Welcome', status='draft',
        )
        self.trigger = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.TRIGGER_CONTACT_CREATED,
        )
        self.tag = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.ACTION_ADD_TAG,
            config={'tag_id': ''},
        )
        self.wait = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.ACTION_WAIT,
            config={'duration': 1, 'unit': 'days'},
        )
        WorkflowEdge.objects.create(
            workflow=self.workflow, source_node=self.trigger,
            target_node=self.tag,
        )
        WorkflowEdge.objects.create(
            workflow=self.workflow, source_node=self.tag,
            target_node=self.wait,
        )

        self.url = reverse('workflow-detail', args=[self.workflow.id])

    def _nodes_payload(self):
        return [
            {
                'id': str(node.id),
                'node_type': node.node_type,
                'position_x': node.position_x,
                'position_y': node.position_y,
                'config': node.config,
                'label': node.label,
            }
            for node in self.workflow.nodes.all()
        ]

    def _edge(self, source, target, branch='default'):
        return {
            'source': str(source.id),
            'target': str(target.id),
            'sourceHandle': branch,
            'targetHandle': 'default',
            'type': branch,
        }

    def test_removing_one_connection_persists(self):
        response = self.client.patch(
            self.url,
            {
                'nodes': self._nodes_payload(),
                'edges': [self._edge(self.trigger, self.tag)],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.workflow.edges.count(), 1)
        remaining = self.workflow.edges.get()
        self.assertEqual(remaining.source_node.node_type, self.trigger.node_type)

    def test_removing_every_connection_persists(self):
        """An empty list must mean "none", not "leave them alone"."""
        response = self.client.patch(
            self.url,
            {'nodes': self._nodes_payload(), 'edges': []},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.workflow.edges.count(), 0)

    def test_edges_sent_without_nodes_are_applied(self):
        """
        The bug: this payload was accepted and silently ignored, because the
        edge write was nested inside the node write.
        """
        response = self.client.patch(
            self.url, {'edges': []}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.workflow.edges.count(), 0)
        # The steps themselves must survive a connections-only save.
        self.assertEqual(self.workflow.nodes.count(), 3)

    def test_a_connections_only_save_keeps_node_configuration(self):
        response = self.client.patch(
            self.url,
            {'edges': [self._edge(self.trigger, self.wait)]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.wait.refresh_from_db()
        self.assertEqual(self.wait.config['duration'], 1)

    def test_a_save_that_touches_neither_leaves_the_connections_alone(self):
        """Renaming the workflow must not wipe its wiring."""
        response = self.client.patch(self.url, {'name': 'Renamed'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.workflow.edges.count(), 2)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.name, 'Renamed')

    def test_a_branch_name_too_long_for_the_column_is_stored_as_named(self):
        """
        A switch node names its own paths, and the name rides in
        source_handle. edge_type is a narrow enumerated column, so a long
        path name would have overflowed it.
        """
        switch = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.CONDITION_SWITCH,
            config={'branches': [{'name': 'Enterprise customers', 'rules': []}]},
        )
        response = self.client.patch(
            self.url,
            {
                'nodes': self._nodes_payload(),
                'edges': [self._edge(switch, self.tag, 'Enterprise customers')],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        edge = self.workflow.edges.get()
        self.assertEqual(edge.edge_type, 'named')
        # The branch itself is not lost — it is what the executor matches on.
        self.assertEqual(edge.source_handle, 'Enterprise customers')

    def test_a_known_branch_keeps_its_own_type(self):
        condition = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.CONDITION_IF_ELSE,
            config={'rules': []},
        )
        self.client.patch(
            self.url,
            {
                'nodes': self._nodes_payload(),
                'edges': [
                    self._edge(condition, self.tag, 'true'),
                    self._edge(condition, self.wait, 'false'),
                ],
            },
            format='json',
        )

        self.assertEqual(
            {edge.edge_type for edge in self.workflow.edges.all()},
            {'true', 'false'},
        )

    def test_an_edge_naming_a_step_that_is_gone_is_skipped(self):
        """Deleting a step takes its connections with it."""
        response = self.client.patch(
            self.url,
            {
                'nodes': [
                    node for node in self._nodes_payload()
                    if node['id'] != str(self.wait.id)
                ],
                'edges': [
                    self._edge(self.trigger, self.tag),
                    self._edge(self.tag, self.wait),
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.workflow.nodes.count(), 2)
        self.assertEqual(self.workflow.edges.count(), 1)

    def test_another_accounts_workflow_cannot_be_rewired(self):
        other = Organization.objects.create(name='Other Ltd', slug='other')
        theirs = Workflow.objects.create(organization=other, name='Theirs')

        response = self.client.patch(
            reverse('workflow-detail', args=[theirs.id]),
            {'edges': []},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
