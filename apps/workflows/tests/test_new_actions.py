"""
The actions added alongside the catalogue.

Most are thin wiring to a service another app already owns, so what is worth
pinning is the boundary: that each refuses an object from another account,
and that the ones which touch a person's inbox or subscription state do the
right thing when asked twice.
"""
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import Organization, User
from apps.contacts.models import Contact
from apps.crm.models import CRMTask, Pipeline, Stage
from apps.segments.models import Segment, SegmentMembership
from apps.sequences.models import EmailSequence
from apps.workflows.models import Workflow, WorkflowExecution, WorkflowNode
from apps.workflows.services import WorkflowExecutionService


class ActionTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.other = Organization.objects.create(name='Other Ltd', slug='other')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.contact = Contact.objects.create(
            organization=self.org, email='ada@example.com', first_name='Ada',
        )
        self.workflow = Workflow.objects.create(
            organization=self.org, name='Flow', status='active',
        )
        self.execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=self.contact, status='active',
        )

    def _run(self, node_type, config):
        node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=node_type, config=config,
        )
        return WorkflowExecutionService._handle_node(self.execution, node)


class SegmentActionTests(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.static = Segment.objects.create(
            organization=self.org, name='VIPs', segment_type='static',
        )

    def test_a_contact_is_added_to_a_static_segment(self):
        self._run(
            WorkflowNode.ACTION_ADD_TO_SEGMENT,
            {'segment_id': str(self.static.id)},
        )
        self.assertTrue(
            SegmentMembership.objects.filter(
                segment=self.static, contact=self.contact
            ).exists()
        )

    def test_a_contact_is_removed_again(self):
        SegmentMembership.objects.create(segment=self.static, contact=self.contact)

        self._run(
            WorkflowNode.ACTION_REMOVE_FROM_SEGMENT,
            {'segment_id': str(self.static.id)},
        )
        self.assertFalse(
            SegmentMembership.objects.filter(
                segment=self.static, contact=self.contact
            ).exists()
        )

    def test_a_dynamic_segment_is_refused_with_a_reason(self):
        """
        Writing a membership row to a dynamic segment would be overwritten by
        its own rules, so the step would look like it had done nothing.
        """
        dynamic = Segment.objects.create(
            organization=self.org, name='Engaged', segment_type='dynamic',
            rules={'match': 'all', 'conditions': []},
        )
        with self.assertRaises(ValueError) as caught:
            self._run(
                WorkflowNode.ACTION_ADD_TO_SEGMENT,
                {'segment_id': str(dynamic.id)},
            )
        self.assertIn('dynamic', str(caught.exception))

    def test_another_accounts_segment_is_refused(self):
        theirs = Segment.objects.create(
            organization=self.other, name='Theirs', segment_type='static',
        )
        with self.assertRaises(ValueError):
            self._run(
                WorkflowNode.ACTION_ADD_TO_SEGMENT,
                {'segment_id': str(theirs.id)},
            )
        self.assertFalse(SegmentMembership.objects.exists())


class SequenceActionTests(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.sequence = EmailSequence.objects.create(
            organization=self.org, name='Onboarding', status='active',
        )

    def test_a_contact_is_enrolled(self):
        with patch(
            'apps.sequences.services.SequenceEnrollmentService.enroll_contact'
        ) as enroll:
            enroll.return_value = None
            result = self._run(
                WorkflowNode.ACTION_ENROLL_SEQUENCE,
                {'sequence_id': str(self.sequence.id)},
            )

        enroll.assert_called_once()
        self.assertEqual(
            result['output']['sequence_id'], str(self.sequence.id)
        )

    def test_another_accounts_sequence_is_refused(self):
        theirs = EmailSequence.objects.create(
            organization=self.other, name='Theirs', status='active',
        )
        with self.assertRaises(ValueError):
            self._run(
                WorkflowNode.ACTION_ENROLL_SEQUENCE,
                {'sequence_id': str(theirs.id)},
            )


class WorkflowActionTests(ActionTestCase):
    def test_another_workflow_is_started(self):
        other_flow = Workflow.objects.create(
            organization=self.org, name='Second', status='active',
        )
        WorkflowNode.objects.create(
            workflow=other_flow, node_type=WorkflowNode.TRIGGER_CONTACT_CREATED,
        )

        with patch.object(WorkflowExecutionService, '_queue_node_execution'):
            result = self._run(
                WorkflowNode.ACTION_ENROLL_WORKFLOW,
                {'workflow_id': str(other_flow.id)},
            )

        self.assertTrue(result['output']['started'])
        self.assertTrue(
            WorkflowExecution.objects.filter(
                workflow=other_flow, contact=self.contact
            ).exists()
        )

    def test_a_workflow_cannot_start_itself(self):
        with self.assertRaises(ValueError) as caught:
            self._run(
                WorkflowNode.ACTION_ENROLL_WORKFLOW,
                {'workflow_id': str(self.workflow.id)},
            )
        self.assertIn('cannot start itself', str(caught.exception))

    def test_the_other_workflows_entry_rules_still_apply(self):
        """Enrolling must not be a way past someone else's re-entry limit."""
        other_flow = Workflow.objects.create(
            organization=self.org, name='Second', status='active',
            reentry=Workflow.REENTRY_ONCE,
        )
        WorkflowNode.objects.create(
            workflow=other_flow, node_type=WorkflowNode.TRIGGER_CONTACT_CREATED,
        )
        WorkflowExecution.objects.create(
            workflow=other_flow, contact=self.contact, status='completed',
        )

        with patch.object(WorkflowExecutionService, '_queue_node_execution'):
            result = self._run(
                WorkflowNode.ACTION_ENROLL_WORKFLOW,
                {'workflow_id': str(other_flow.id)},
            )

        self.assertFalse(result['output']['started'])

    def test_a_run_of_another_workflow_is_cancelled(self):
        other_flow = Workflow.objects.create(
            organization=self.org, name='Second', status='active',
            contacts_active=1,
        )
        run = WorkflowExecution.objects.create(
            workflow=other_flow, contact=self.contact, status='active',
        )

        result = self._run(
            WorkflowNode.ACTION_REMOVE_FROM_WORKFLOW,
            {'workflow_id': str(other_flow.id)},
        )

        run.refresh_from_db()
        self.assertEqual(run.status, 'cancelled')
        self.assertEqual(result['output']['cancelled'], 1)

    def test_another_accounts_workflow_is_refused(self):
        theirs = Workflow.objects.create(
            organization=self.other, name='Theirs', status='active',
        )
        with self.assertRaises(ValueError):
            self._run(
                WorkflowNode.ACTION_REMOVE_FROM_WORKFLOW,
                {'workflow_id': str(theirs.id)},
            )


class ContactActionTests(ActionTestCase):
    def test_a_contact_is_unsubscribed(self):
        self._run(WorkflowNode.ACTION_UNSUBSCRIBE, {})

        self.contact.refresh_from_db()
        self.assertFalse(self.contact.is_subscribed)
        self.assertIsNotNone(self.contact.unsubscribed_at)

    def test_unsubscribing_twice_is_not_an_error(self):
        """
        A workflow failing because it did something already true is noise,
        and the end state is what was asked for either way.
        """
        self.contact.is_subscribed = False
        self.contact.save(update_fields=['is_subscribed'])

        result = self._run(WorkflowNode.ACTION_UNSUBSCRIBE, {})
        self.assertFalse(result['output']['is_subscribed'])

    def test_a_note_is_recorded_against_the_contact(self):
        from apps.crm.models import Activity

        self._run(WorkflowNode.ACTION_ADD_NOTE, {'note': 'Asked about pricing'})

        activity = Activity.objects.get(contact=self.contact)
        self.assertEqual(activity.activity_type, 'note')
        self.assertIn('Asked about pricing', activity.description)

    def test_an_empty_note_is_refused(self):
        with self.assertRaises(ValueError):
            self._run(WorkflowNode.ACTION_ADD_NOTE, {'note': '   '})

    def test_an_owner_is_assigned(self):
        self._run(
            WorkflowNode.ACTION_ASSIGN_CONTACT, {'user_id': str(self.user.id)}
        )
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.assigned_to_id, self.user.id)

    def test_a_user_from_another_account_is_refused(self):
        stranger = User.objects.create_user(
            email='them@other.test', password='x', organization=self.other,
            role='owner',
        )
        with self.assertRaises(ValueError):
            self._run(
                WorkflowNode.ACTION_ASSIGN_CONTACT, {'user_id': str(stranger.id)}
            )


class CrmActionTests(ActionTestCase):
    def setUp(self):
        super().setUp()
        self.pipeline = Pipeline.objects.create(
            organization=self.org, name='Sales',
        )
        self.stage = Stage.objects.create(
            pipeline=self.pipeline, name='New', position=0,
        )

    def test_a_deal_is_created_and_linked_to_the_contact(self):
        result = self._run(
            WorkflowNode.ACTION_CREATE_DEAL,
            {'pipeline_id': str(self.pipeline.id), 'value': '500'},
        )

        from apps.crm.models import Deal

        deal = Deal.objects.get(id=result['output']['deal_id'])
        self.assertEqual(deal.organization, self.org)
        self.assertEqual(deal.stage, self.stage)
        self.assertTrue(deal.deal_contacts.filter(contact=self.contact).exists())

    def test_a_deal_with_no_title_is_named_after_the_contact(self):
        result = self._run(
            WorkflowNode.ACTION_CREATE_DEAL,
            {'pipeline_id': str(self.pipeline.id)},
        )
        from apps.crm.models import Deal

        self.assertEqual(Deal.objects.get(id=result['output']['deal_id']).title, 'Ada')

    def test_another_accounts_pipeline_is_refused(self):
        theirs = Pipeline.objects.create(organization=self.other, name='Theirs')
        with self.assertRaises(ValueError):
            self._run(
                WorkflowNode.ACTION_CREATE_DEAL, {'pipeline_id': str(theirs.id)}
            )

    def test_a_task_is_created(self):
        result = self._run(
            WorkflowNode.ACTION_CREATE_TASK,
            {'title': 'Call {{first_name}}', 'priority': 'high', 'due_in_days': 2},
        )

        task = CRMTask.objects.get(id=result['output']['task_id'])
        # Merge tags are resolved, so the salesperson sees a name.
        self.assertEqual(task.title, 'Call Ada')
        self.assertEqual(task.priority, 'high')
        self.assertEqual(task.contact, self.contact)

    def test_a_task_with_no_title_is_refused(self):
        with self.assertRaises(ValueError):
            self._run(WorkflowNode.ACTION_CREATE_TASK, {'title': ''})


class NotifyTests(ActionTestCase):
    def test_a_colleague_is_emailed(self):
        from apps.core.mail import MailResult

        with patch(
            'apps.core.mail.send_transactional_email',
            return_value=MailResult(True, ''),
        ) as send:
            result = self._run(
                WorkflowNode.ACTION_NOTIFY_TEAM,
                {'user_id': str(self.user.id), 'subject': 'New lead'},
            )

        send.assert_called_once()
        self.assertEqual(result['output']['notified'], self.user.email)
        # Internal mail, not marketing: it goes through the transactional path
        # so it is not suppressed by the contact's own preferences.
        self.assertEqual(
            send.call_args.kwargs['template'],
            'workflows/email/team_notification',
        )

    def test_a_failure_is_surfaced_rather_than_swallowed(self):
        from apps.core.mail import MailResult

        with patch(
            'apps.core.mail.send_transactional_email',
            return_value=MailResult(False, 'no sending identity'),
        ):
            with self.assertRaises(RuntimeError) as caught:
                self._run(
                    WorkflowNode.ACTION_NOTIFY_TEAM,
                    {'user_id': str(self.user.id), 'subject': 'New lead'},
                )
        self.assertIn('no sending identity', str(caught.exception))

    def test_notifying_nobody_is_refused(self):
        with self.assertRaises(ValueError):
            self._run(WorkflowNode.ACTION_NOTIFY_TEAM, {'subject': 'Hello'})


class SplitTestTests(ActionTestCase):
    def test_the_same_execution_always_takes_the_same_branch(self):
        """
        A contact who flips branch on a retry would receive both variants,
        which is exactly what an A/B test must never do.
        """
        node = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.CONDITION_SPLIT_TEST,
            config={'percent_a': 50},
        )
        first = WorkflowExecutionService._handle_split_test(self.execution, node)
        second = WorkflowExecutionService._handle_split_test(self.execution, node)

        self.assertEqual(first['branch'], second['branch'])

    def test_everyone_goes_to_a_at_a_hundred_percent(self):
        node = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.CONDITION_SPLIT_TEST,
            config={'percent_a': 100},
        )
        self.assertEqual(
            WorkflowExecutionService._handle_split_test(self.execution, node)['branch'],
            'a',
        )

    def test_everyone_goes_to_b_at_zero(self):
        node = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.CONDITION_SPLIT_TEST,
            config={'percent_a': 0},
        )
        self.assertEqual(
            WorkflowExecutionService._handle_split_test(self.execution, node)['branch'],
            'b',
        )

    def test_a_nonsense_percentage_does_not_crash(self):
        node = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.CONDITION_SPLIT_TEST,
            config={'percent_a': 'half'},
        )
        self.assertIn(
            WorkflowExecutionService._handle_split_test(self.execution, node)['branch'],
            ('a', 'b'),
        )


class ConditionTests(ActionTestCase):
    def test_a_contact_property_rule_uses_the_segment_engine(self):
        self.contact.company = 'Acme Corp'
        self.contact.save(update_fields=['company'])

        node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.CONDITION_IF_ELSE,
            config={
                'logic': 'all',
                'rules': [
                    {'field': 'company', 'operator': 'contains', 'value': 'acme'},
                ],
            },
        )
        result = WorkflowExecutionService._handle_condition(self.execution, node)
        self.assertEqual(result['branch'], 'true')

    def test_a_rule_that_does_not_match_takes_the_false_branch(self):
        node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.CONDITION_IF_ELSE,
            config={
                'logic': 'all',
                'rules': [
                    {'field': 'company', 'operator': 'equals', 'value': 'Nope'},
                ],
            },
        )
        result = WorkflowExecutionService._handle_condition(self.execution, node)
        self.assertEqual(result['branch'], 'false')

    def test_any_logic_needs_only_one_match(self):
        self.contact.company = 'Acme Corp'
        self.contact.save(update_fields=['company'])

        node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.CONDITION_IF_ELSE,
            config={
                'logic': 'any',
                'rules': [
                    {'field': 'company', 'operator': 'equals', 'value': 'Nope'},
                    {'field': 'company', 'operator': 'contains', 'value': 'Acme'},
                ],
            },
        )
        result = WorkflowExecutionService._handle_condition(self.execution, node)
        self.assertEqual(result['branch'], 'true')

    def test_a_behaviour_rule_reads_events_since_entering(self):
        from apps.campaigns.models import Campaign, CampaignRecipient
        from django.utils import timezone

        campaign = Campaign.objects.create(
            organization=self.org, name='Newsletter', subject='Hi',
        )
        CampaignRecipient.objects.create(
            campaign=campaign, contact=self.contact, email=self.contact.email,
            opened_at=timezone.now(),
        )

        node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.CONDITION_IF_ELSE,
            config={
                'logic': 'all',
                'rules': [
                    {'field': 'event.email_opened', 'operator': 'is_true',
                     'value': ''},
                ],
            },
        )
        result = WorkflowExecutionService._handle_condition(self.execution, node)
        self.assertEqual(result['branch'], 'true')

    def test_an_open_from_before_they_entered_does_not_count(self):
        """"Did they open the one we just sent" must mean what it says."""
        from datetime import timedelta

        from apps.campaigns.models import Campaign, CampaignRecipient
        from django.utils import timezone

        campaign = Campaign.objects.create(
            organization=self.org, name='Old', subject='Hi',
        )
        CampaignRecipient.objects.create(
            campaign=campaign, contact=self.contact, email=self.contact.email,
            opened_at=timezone.now() - timedelta(days=365),
        )

        node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.CONDITION_IF_ELSE,
            config={
                'logic': 'all',
                'rules': [
                    {'field': 'event.email_opened', 'operator': 'is_true',
                     'value': ''},
                ],
            },
        )
        result = WorkflowExecutionService._handle_condition(self.execution, node)
        self.assertEqual(result['branch'], 'false')

    def test_a_malformed_rule_is_false_rather_than_an_exception(self):
        """A bad rule must not fail the execution three times and alert an admin."""
        node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.CONDITION_IF_ELSE,
            config={
                'logic': 'all',
                'rules': [{'field': 'not_a_field', 'operator': 'equals',
                           'value': 'x'}],
            },
        )
        result = WorkflowExecutionService._handle_condition(self.execution, node)
        self.assertEqual(result['branch'], 'false')
