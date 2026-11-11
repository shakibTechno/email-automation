"""
The AI generator, and the inbound webhook.

Both take input from outside and turn it into a workflow run, so both are
tested on what they refuse as much as on what they build.
"""
import json
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import Organization, User
from apps.ai_assistant.generators import workflows as generator
from apps.ai_assistant.models import GenerationJob
from apps.contacts.models import Contact, Tag
from apps.templates.models import EmailTemplate
from apps.workflows.models import Workflow, WorkflowNode
from apps.workflows.services import WorkflowExecutionService


class GeneratorTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.tag = Tag.objects.create(organization=self.org, name='Engaged')
        self.template = EmailTemplate.objects.create(
            organization=self.org, name='Welcome Email', subject='Hi',
            html_content='<p>Hi</p>',
        )
        self.job = GenerationJob.objects.create(
            organization=self.org, created_by=self.user,
            kind=GenerationJob.KIND_WORKFLOW, prompt='Welcome new signups',
        )

    def _payload(self, **overrides):
        base = {
            'name': 'Welcome series',
            'description': 'Greet new signups',
            'trigger': {
                'type': 'trigger_contact_created', 'form_name': '',
                'tag_name': '', 'segment_name': '', 'path': '', 'field': '',
            },
            'steps': [
                self._step('action_send_email', template_name='Welcome Email',
                           label='Say hello'),
                self._step('action_wait', wait_amount=3, wait_unit='days',
                           label='Wait three days'),
                self._step('action_add_tag', tag_name='Engaged',
                           label='Tag them'),
            ],
        }
        base.update(overrides)
        return base

    @staticmethod
    def _step(step_type, **values):
        step = {
            'type': step_type, 'label': '', 'template_name': '', 'tag_name': '',
            'segment_name': '', 'sequence_name': '', 'wait_amount': 0,
            'wait_unit': 'days', 'points': 0, 'field': '', 'value': '',
            'text': '', 'subject': '', 'condition': '',
            'if_true': [], 'if_false': [],
        }
        step.update(values)
        return step


class SchemaTests(GeneratorTestCase):
    def test_the_schema_is_json(self):
        self.assertIsInstance(json.dumps(generator.SCHEMA), str)

    def test_every_choice_it_offers_is_a_real_node_type(self):
        from apps.workflows import catalog

        for choice in generator.TRIGGER_CHOICES + generator.STEP_CHOICES:
            with self.subTest(choice):
                self.assertTrue(catalog.exists(choice))

    def test_the_model_is_never_asked_for_coordinates_or_ids(self):
        """
        A model asked for x/y or UUIDs produces a tangle pointing at nothing.
        It describes the shape; the geometry is computed here.
        """
        text = json.dumps(generator.SCHEMA)
        for forbidden in ('position_x', 'position_y', 'node_id', 'edge'):
            self.assertNotIn(forbidden, text)


class PromptTests(GeneratorTestCase):
    def test_the_prompt_carries_the_accounts_own_assets(self):
        """
        Without the inventory the model invents "Welcome Email Template",
        every node arrives pointing at nothing, and the feature feels useless.
        """
        prompt = generator.build_user_prompt(
            prompt='Welcome new signups', organization=self.org,
        )

        self.assertIn('Welcome Email', prompt)
        self.assertIn('Engaged', prompt)
        self.assertIn('Only use the names listed above', prompt)

    def test_an_empty_list_says_so_rather_than_being_omitted(self):
        prompt = generator.build_user_prompt(prompt='x', organization=self.org)
        self.assertIn('(none)', prompt)

    def test_it_still_works_without_an_organization(self):
        self.assertIn('Goal:', generator.build_user_prompt(prompt='Hello'))


class BuildTests(GeneratorTestCase):
    def test_a_workflow_is_built_from_the_payload(self):
        workflow = generator.create(self.job, self._payload())

        self.assertEqual(workflow.organization, self.org)
        self.assertEqual(workflow.name, 'Welcome series')
        self.assertEqual(workflow.nodes.count(), 4)  # trigger + three steps

    def test_it_always_arrives_as_a_draft(self):
        workflow = generator.create(self.job, self._payload())
        self.assertEqual(workflow.status, 'draft')

    def test_names_are_resolved_to_the_accounts_real_ids(self):
        workflow = generator.create(self.job, self._payload())

        send = workflow.nodes.get(node_type=WorkflowNode.ACTION_SEND_EMAIL)
        self.assertEqual(send.config['template_id'], str(self.template.id))
        tag = workflow.nodes.get(node_type=WorkflowNode.ACTION_ADD_TAG)
        self.assertEqual(tag.config['tag_id'], str(self.tag.id))

    def test_a_name_the_account_does_not_have_is_left_empty(self):
        payload = self._payload(steps=[
            self._step('action_add_tag', tag_name='Does Not Exist'),
        ])
        workflow = generator.create(self.job, payload)

        tag = workflow.nodes.get(node_type=WorkflowNode.ACTION_ADD_TAG)
        self.assertEqual(tag.config.get('tag_id', ''), '')

    def test_the_steps_are_wired_in_order(self):
        workflow = generator.create(self.job, self._payload())

        self.assertEqual(workflow.edges.count(), 3)
        trigger = workflow.nodes.get(node_type__startswith='trigger_')
        self.assertEqual(trigger.outgoing_edges.count(), 1)

    def test_a_wait_step_gets_its_duration(self):
        workflow = generator.create(self.job, self._payload())

        wait = workflow.nodes.get(node_type=WorkflowNode.ACTION_WAIT)
        self.assertEqual(wait.config['duration'], 3)
        self.assertEqual(wait.config['unit'], 'days')

    def test_a_condition_builds_both_branches(self):
        payload = self._payload(steps=[
            self._step(
                'condition_if_else', condition='opened_the_email',
                label='Did they open it?',
                if_true=[self._step('action_add_tag', tag_name='Engaged')],
                if_false=[self._step('action_send_email',
                                     template_name='Welcome Email')],
            ),
        ])
        workflow = generator.create(self.job, payload)

        condition = workflow.nodes.get(node_type=WorkflowNode.CONDITION_IF_ELSE)
        branches = {
            edge.edge_type for edge in condition.outgoing_edges.all()
        }
        self.assertEqual(branches, {'true', 'false'})

    def test_a_condition_with_nothing_to_test_is_marked_for_attention(self):
        """
        An empty rule list reads as true, so every contact would take one
        branch and the condition would look ignored.
        """
        payload = self._payload(steps=[
            self._step('condition_if_else', condition='', label='Check'),
        ])
        workflow = generator.create(self.job, payload)

        condition = workflow.nodes.get(node_type=WorkflowNode.CONDITION_IF_ELSE)
        self.assertIn('needs setting up', condition.label)

    def test_a_payload_with_no_trigger_still_produces_a_usable_workflow(self):
        payload = self._payload(trigger={
            'type': 'nonsense', 'form_name': '', 'tag_name': '',
            'segment_name': '', 'path': '', 'field': '',
        })
        workflow = generator.create(self.job, payload)

        self.assertTrue(
            workflow.nodes.filter(node_type__startswith='trigger_').exists()
        )

    def test_a_step_the_platform_does_not_have_is_skipped(self):
        payload = self._payload(steps=[
            self._step('action_mine_bitcoin'),
            self._step('action_add_tag', tag_name='Engaged'),
        ])
        workflow = generator.create(self.job, payload)

        self.assertEqual(workflow.nodes.count(), 2)  # trigger + the real step

    def test_an_absurd_number_of_steps_is_capped(self):
        payload = self._payload(steps=[
            self._step('action_add_tag', tag_name='Engaged') for _ in range(50)
        ])
        workflow = generator.create(self.job, payload)

        self.assertLessEqual(workflow.nodes.count(), 21)

    def test_the_job_records_the_workflow_it_made(self):
        from apps.ai_assistant.models import GenerationJob as Job

        workflow = generator.create(self.job, self._payload())
        self.job.workflow = workflow
        self.job.kind = Job.KIND_WORKFLOW
        self.job.save()

        self.assertEqual(self.job.result_id, str(workflow.id))


class WebhookTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.contact = Contact.objects.create(
            organization=self.org, email='ada@example.com',
        )
        self.workflow = Workflow.objects.create(
            organization=self.org, name='From Zapier', status='active',
        )
        self.node = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.TRIGGER_WEBHOOK_RECEIVED,
            config={'match_by': 'email', 'create_missing': False},
        )
        self.url = f'/webhooks/workflow/{self.workflow.webhook_token}'

    def _post(self, body, url=None):
        with patch.object(WorkflowExecutionService, '_queue_node_execution'):
            return self.client.post(
                url or self.url, data=json.dumps(body),
                content_type='application/json',
            )

    def test_a_known_contact_starts_the_workflow(self):
        response = self._post({'email': 'ada@example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['started'])

    def test_the_email_match_ignores_case(self):
        self.assertEqual(self._post({'email': 'ADA@EXAMPLE.COM'}).status_code, 200)

    def test_an_unknown_contact_is_refused_when_creating_is_off(self):
        response = self._post({'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, 422)

    def test_an_unknown_contact_is_created_when_that_is_allowed(self):
        self.node.config = {'match_by': 'email', 'create_missing': True}
        self.node.save(update_fields=['config'])

        response = self._post({'email': 'grace@example.com', 'first_name': 'Grace'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['contact_created'])
        created = Contact.objects.get(email='grace@example.com')
        self.assertEqual(created.organization, self.org)

    def test_a_bad_token_is_a_404(self):
        response = self._post(
            {'email': 'ada@example.com'},
            url='/webhooks/workflow/00000000-0000-0000-0000-000000000000',
        )
        self.assertEqual(response.status_code, 404)

    def test_a_paused_workflow_answers_exactly_like_a_bad_token(self):
        """A caller holding a token should not learn which it is."""
        self.workflow.status = 'paused'
        self.workflow.save(update_fields=['status'])

        response = self._post({'email': 'ada@example.com'})
        self.assertEqual(response.status_code, 404)

    def test_the_token_decides_the_tenant_not_the_body(self):
        """A payload naming another account's contact must not reach them."""
        other = Organization.objects.create(name='Other', slug='other')
        theirs = Contact.objects.create(
            organization=other, email='them@other.test',
        )

        response = self._post({'email': 'them@other.test'})

        self.assertEqual(response.status_code, 422)
        self.assertFalse(
            Workflow.objects.filter(executions__contact=theirs).exists()
        )

    def test_a_body_that_is_not_json_is_refused(self):
        response = self.client.post(
            self.url, data='not json', content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_a_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_the_workflows_own_entry_rules_still_apply(self):
        from apps.workflows.models import WorkflowExecution

        self.workflow.reentry = Workflow.REENTRY_ONCE
        self.workflow.save(update_fields=['reentry'])
        WorkflowExecution.objects.create(
            workflow=self.workflow, contact=self.contact, status='completed',
        )

        response = self._post({'email': 'ada@example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['started'])
