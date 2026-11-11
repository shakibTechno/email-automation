"""
Moving a workflow between accounts.

The shape is the easy part. The hard part is the references: node config is
full of ids for tags, templates, segments and pipelines, and every one of them
belongs to whoever exported the file. Carried across unchanged they are broken
at best and another tenant's data at worst.
"""
import json

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, User
from apps.contacts.models import Tag
from apps.segments.models import Segment
from apps.templates.models import EmailTemplate
from apps.workflows import definition
from apps.workflows.models import Workflow, WorkflowEdge, WorkflowNode


class DefinitionTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.other = Organization.objects.create(name='Other Ltd', slug='other')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.tag = Tag.objects.create(organization=self.org, name='VIP')
        self.template = EmailTemplate.objects.create(
            organization=self.org, name='Welcome', subject='Hi',
            html_content='<p>Hi</p>',
        )

        self.workflow = Workflow.objects.create(
            organization=self.org, name='Welcome series', status='active',
            description='Greets new signups', reentry=Workflow.REENTRY_ALWAYS,
            reentry_cooldown_days=3, contacts_entered=412,
        )
        self.trigger = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.TRIGGER_CONTACT_CREATED,
            label='New contact', position_x=0, position_y=0,
        )
        self.send = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.ACTION_SEND_EMAIL,
            label='Say hello', position_x=0, position_y=150,
            config={'template_id': str(self.template.id)},
        )
        self.tag_node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.ACTION_ADD_TAG,
            label='Mark as VIP', position_x=0, position_y=300,
            config={'tag_id': str(self.tag.id)},
        )
        WorkflowEdge.objects.create(
            workflow=self.workflow, source_node=self.trigger,
            target_node=self.send,
        )
        WorkflowEdge.objects.create(
            workflow=self.workflow, source_node=self.send,
            target_node=self.tag_node,
        )


class ExportTests(DefinitionTestCase):
    def test_the_export_carries_the_steps_and_connections(self):
        payload = definition.export_definition(self.workflow)

        self.assertEqual(payload['format'], definition.FORMAT)
        self.assertEqual(len(payload['nodes']), 3)
        self.assertEqual(len(payload['edges']), 2)

    def test_each_reference_is_recorded_by_name(self):
        """Without the name there is nothing to re-point by."""
        payload = definition.export_definition(self.workflow)
        by_id = {node['id']: node for node in payload['nodes']}

        self.assertEqual(
            by_id[str(self.tag_node.id)]['assets']['tag_id'],
            {'kind': 'tag', 'name': 'VIP'},
        )
        self.assertEqual(
            by_id[str(self.send.id)]['assets']['template_id']['name'], 'Welcome'
        )

    def test_the_design_travels_but_the_history_does_not(self):
        """Counters and status describe this copy, not the workflow."""
        payload = definition.export_definition(self.workflow)

        self.assertEqual(payload['workflow']['reentry'], Workflow.REENTRY_ALWAYS)
        self.assertEqual(payload['workflow']['reentry_cooldown_days'], 3)
        for leaked in ('status', 'contacts_entered', 'webhook_token', 'id'):
            self.assertNotIn(leaked, payload['workflow'])

    def test_the_export_survives_json(self):
        payload = definition.export_definition(self.workflow)
        self.assertEqual(
            json.loads(json.dumps(payload))['workflow']['name'], 'Welcome series'
        )


class ImportTests(DefinitionTestCase):
    def _export(self):
        return json.loads(json.dumps(definition.export_definition(self.workflow)))

    def test_a_round_trip_inside_one_account_keeps_every_reference(self):
        copy, report = definition.build_from_definition(
            self.org, self._export(), user=self.user,
        )

        self.assertEqual(report['unresolved'], [])
        tag_node = copy.nodes.get(node_type=WorkflowNode.ACTION_ADD_TAG)
        self.assertEqual(tag_node.config['tag_id'], str(self.tag.id))

    def test_an_import_always_arrives_as_a_draft(self):
        """Nothing that has not been reviewed may start mailing."""
        copy, _ = definition.build_from_definition(self.org, self._export())
        self.assertEqual(copy.status, 'draft')

    def test_the_connections_are_rebuilt_between_the_new_steps(self):
        copy, report = definition.build_from_definition(self.org, self._export())

        self.assertEqual(report['edges_created'], 2)
        for edge in copy.edges.all():
            self.assertEqual(edge.source_node.workflow_id, copy.id)
            self.assertEqual(edge.target_node.workflow_id, copy.id)

    def test_references_are_matched_by_name_in_the_other_account(self):
        """The whole point of carrying names: the ids mean nothing here."""
        their_tag = Tag.objects.create(organization=self.other, name='VIP')
        their_template = EmailTemplate.objects.create(
            organization=self.other, name='Welcome', subject='Hi',
            html_content='<p>Hi</p>',
        )

        copy, report = definition.build_from_definition(self.other, self._export())

        self.assertEqual(report['unresolved'], [])
        self.assertEqual(
            copy.nodes.get(node_type=WorkflowNode.ACTION_ADD_TAG).config['tag_id'],
            str(their_tag.id),
        )
        self.assertEqual(
            copy.nodes.get(node_type=WorkflowNode.ACTION_SEND_EMAIL)
            .config['template_id'],
            str(their_template.id),
        )

    def test_an_unmatched_reference_is_cleared_not_carried_over(self):
        """
        An id from another account must not survive into this one, even
        unusable: that is how one tenant's data ends up addressed by another's
        workflow.
        """
        copy, report = definition.build_from_definition(self.other, self._export())

        tag_node = copy.nodes.get(node_type=WorkflowNode.ACTION_ADD_TAG)
        self.assertEqual(tag_node.config['tag_id'], '')
        self.assertNotEqual(tag_node.config['tag_id'], str(self.tag.id))

    def test_what_could_not_be_placed_is_reported_with_its_step(self):
        _, report = definition.build_from_definition(self.other, self._export())

        names = {item['name'] for item in report['unresolved']}
        self.assertEqual(names, {'VIP', 'Welcome'})
        self.assertIn('Mark as VIP', report['needs_attention'])

    def test_the_name_can_be_overridden(self):
        copy, _ = definition.build_from_definition(
            self.org, self._export(), name_override='Second copy',
        )
        self.assertEqual(copy.name, 'Second copy')

    def test_a_hostile_reentry_value_is_dropped_not_stored(self):
        payload = self._export()
        payload['workflow']['reentry'] = 'whatever-i-like'

        copy, _ = definition.build_from_definition(self.org, payload)
        self.assertEqual(copy.reentry, Workflow.REENTRY_ONE_AT_A_TIME)

    def test_an_unknown_node_type_in_the_file_is_skipped(self):
        payload = self._export()
        payload['nodes'].append({
            'id': 'x', 'node_type': 'action_mine_bitcoin', 'config': {},
            'position_x': 0, 'position_y': 0, 'label': '', 'assets': {},
        })

        copy, _ = definition.build_from_definition(self.org, payload)
        self.assertEqual(copy.nodes.count(), 3)


class ValidationTests(DefinitionTestCase):
    def _export(self):
        return json.loads(json.dumps(definition.export_definition(self.workflow)))

    def test_a_good_file_passes(self):
        self.assertIsNotNone(definition.validate_definition(self._export()))

    def test_something_that_is_not_a_workflow_is_refused(self):
        with self.assertRaises(definition.DefinitionError):
            definition.validate_definition({'hello': 'world'})

    def test_a_newer_export_is_refused_rather_than_half_read(self):
        payload = self._export()
        payload['version'] = definition.VERSION + 1
        with self.assertRaises(definition.DefinitionError) as caught:
            definition.validate_definition(payload)
        self.assertIn('newer version', str(caught.exception))

    def test_an_unknown_step_is_named_rather_than_dropped(self):
        """
        Silently losing a step gives a workflow that looks complete and does
        something different.
        """
        payload = self._export()
        payload['nodes'][0]['node_type'] = 'action_mine_bitcoin'

        with self.assertRaises(definition.DefinitionError) as caught:
            definition.validate_definition(payload)
        self.assertIn('action_mine_bitcoin', str(caught.exception))

    def test_a_workflow_with_no_trigger_is_refused(self):
        payload = self._export()
        payload['nodes'] = [
            node for node in payload['nodes']
            if not node['node_type'].startswith('trigger_')
        ]
        with self.assertRaises(definition.DefinitionError) as caught:
            definition.validate_definition(payload)
        self.assertIn('no trigger', str(caught.exception))

    def test_an_enormous_file_is_refused(self):
        payload = self._export()
        payload['nodes'] = payload['nodes'] * 100

        with self.assertRaises(definition.DefinitionError) as caught:
            definition.validate_definition(payload)
        self.assertIn('at most', str(caught.exception))

    def test_an_empty_workflow_is_refused(self):
        payload = self._export()
        payload['nodes'] = []
        with self.assertRaises(definition.DefinitionError):
            definition.validate_definition(payload)


class EndpointTests(APITestCase, DefinitionTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_the_catalogue_is_served(self):
        response = self.client.get(reverse('workflow-node-types'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        types = {entry['type'] for entry in response.data['results']}
        # The four that were live in the backend and invisible in the builder.
        for orphan in (
            'trigger_popup_shown', 'trigger_popup_clicked',
            'trigger_lead_score_threshold', 'action_update_lead_score',
        ):
            self.assertIn(orphan, types)

    def test_export_returns_a_downloadable_file(self):
        response = self.client.get(
            reverse('workflow-export', args=[self.workflow.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(response.data['format'], definition.FORMAT)

    def test_another_accounts_workflow_cannot_be_exported(self):
        theirs = Workflow.objects.create(organization=self.other, name='Theirs')
        response = self.client.get(reverse('workflow-export', args=[theirs.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_import_creates_a_draft_and_reports_what_it_could_not_place(self):
        payload = json.loads(json.dumps(definition.export_definition(self.workflow)))

        response = self.client.post(
            reverse('workflow-import-workflow'),
            {'definition': payload, 'name': 'Imported'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['workflow']['status'], 'draft')
        self.assertEqual(response.data['workflow']['name'], 'Imported')
        self.assertEqual(response.data['report']['unresolved'], [])

    def test_a_bad_file_is_refused_with_a_reason(self):
        response = self.client.post(
            reverse('workflow-import-workflow'),
            {'definition': {'nope': True}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not a workflow export', response.data['detail'])

    def test_importing_needs_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            reverse('workflow-import-workflow'), {'definition': {}}, format='json',
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
