"""
Who gets in, how often, and when the workflow is willing to send.

The re-entry rule is the one that mattered most: before it existed,
start_execution refused a contact who had *any* execution row of any status,
so a contact could enter a workflow once in their lifetime. Cart-abandon fired
once per customer ever, re-engagement could never re-engage, and testing a
workflow burned the tester's own contact permanently.
"""
from datetime import time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization, User
from apps.contacts.models import Contact
from apps.segments.models import Segment
from apps.workflows.models import Workflow, WorkflowExecution, WorkflowNode
from apps.workflows.services import WorkflowExecutionService


class EntryTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.contact = Contact.objects.create(
            organization=self.org, email='ada@example.com', first_name='Ada',
        )
        self.workflow = Workflow.objects.create(
            organization=self.org, name='Welcome', status='active',
            created_by=self.user,
        )
        self.trigger = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_type=WorkflowNode.TRIGGER_CONTACT_CREATED,
        )

    def _start(self):
        # The node queues a Celery task; the entry decision is what is under
        # test, not what happens afterwards.
        with patch.object(WorkflowExecutionService, '_queue_node_execution'):
            return WorkflowExecutionService.start_execution(
                self.workflow, self.contact,
            )

    def _finish_run(self, status='completed'):
        WorkflowExecution.objects.filter(
            workflow=self.workflow, contact=self.contact,
        ).update(status=status, completed_at=timezone.now())


class ReEntryTests(EntryTestCase):
    def test_a_first_run_always_starts(self):
        self.assertIsNotNone(self._start())
        self.assertEqual(WorkflowExecution.objects.count(), 1)

    def test_once_ever_refuses_a_second_run(self):
        self.workflow.reentry = Workflow.REENTRY_ONCE
        self.workflow.save(update_fields=['reentry'])

        self._start()
        self._finish_run()

        self.assertIsNone(self._start())
        self.assertEqual(WorkflowExecution.objects.count(), 1)

    def test_once_ever_refuses_even_after_a_cancelled_run(self):
        """
        The old behaviour, kept deliberately for workflows that predate the
        setting. A cancelled run still counts as having been through it.
        """
        self.workflow.reentry = Workflow.REENTRY_ONCE
        self.workflow.save(update_fields=['reentry'])

        self._start()
        self._finish_run('cancelled')

        self.assertIsNone(self._start())

    def test_one_at_a_time_lets_them_back_once_the_run_has_finished(self):
        """The whole point: a re-engagement workflow can re-engage."""
        self.assertIsNotNone(self._start())
        self._finish_run()

        self.assertIsNotNone(self._start())
        self.assertEqual(WorkflowExecution.objects.count(), 2)

    def test_one_at_a_time_refuses_while_a_run_is_still_going(self):
        self._start()
        self.assertIsNone(self._start())
        self.assertEqual(WorkflowExecution.objects.count(), 1)

    def test_one_at_a_time_refuses_while_a_run_is_waiting(self):
        """Waiting is mid-flow, not finished — a wait step is not an exit."""
        self._start()
        self._finish_run('waiting')

        self.assertIsNone(self._start())

    def test_always_starts_a_run_even_alongside_a_live_one(self):
        self.workflow.reentry = Workflow.REENTRY_ALWAYS
        self.workflow.save(update_fields=['reentry'])

        self._start()
        self.assertIsNotNone(self._start())
        self.assertEqual(WorkflowExecution.objects.count(), 2)

    def test_a_cooldown_holds_them_out_for_the_given_days(self):
        self.workflow.reentry_cooldown_days = 7
        self.workflow.save(update_fields=['reentry_cooldown_days'])

        self._start()
        self._finish_run()

        self.assertIsNone(self._start())

    def test_the_cooldown_expires(self):
        self.workflow.reentry_cooldown_days = 7
        self.workflow.save(update_fields=['reentry_cooldown_days'])

        self._start()
        self._finish_run()
        WorkflowExecution.objects.update(
            started_at=timezone.now() - timedelta(days=8)
        )

        self.assertIsNotNone(self._start())

    def test_the_refusal_says_which_rule_stopped_them(self):
        self.workflow.reentry = Workflow.REENTRY_ONCE
        self.workflow.save(update_fields=['reentry'])
        self._start()

        reason = WorkflowExecutionService.refusal_to_enter(
            self.workflow, self.contact,
        )
        self.assertIn('already', reason)


class EntrySegmentTests(EntryTestCase):
    def test_a_contact_outside_the_entry_segment_does_not_enter(self):
        segment = Segment.objects.create(
            organization=self.org, name='Irish leads', segment_type='dynamic',
            rules={'match': 'all', 'conditions': [
                {'field': 'country', 'operator': 'equals', 'value': 'IE'},
            ]},
        )
        self.workflow.entry_segment = segment
        self.workflow.save(update_fields=['entry_segment'])

        self.assertIsNone(self._start())
        self.assertIn(
            'entry segment',
            WorkflowExecutionService.refusal_to_enter(self.workflow, self.contact),
        )

    def test_a_contact_inside_it_enters(self):
        self.contact.country = 'IE'
        self.contact.save(update_fields=['country'])
        segment = Segment.objects.create(
            organization=self.org, name='Irish leads', segment_type='dynamic',
            rules={'match': 'all', 'conditions': [
                {'field': 'country', 'operator': 'equals', 'value': 'IE'},
            ]},
        )
        self.workflow.entry_segment = segment
        self.workflow.save(update_fields=['entry_segment'])

        self.assertIsNotNone(self._start())


class SendWindowTests(EntryTestCase):
    def setUp(self):
        super().setUp()
        self.workflow.respect_quiet_hours = True
        self.workflow.send_window_start = time(9, 0)
        self.workflow.send_window_end = time(18, 0)
        self.workflow.save()

    def _at(self, hour, weekday=None):
        """A datetime at `hour` local time, on a Wednesday unless told otherwise."""
        now = timezone.localtime(timezone.now()).replace(
            hour=hour, minute=0, second=0, microsecond=0,
        )
        if weekday is not None:
            now += timedelta(days=(weekday - now.weekday()) % 7)
        return now

    def test_inside_the_window_is_allowed(self):
        self.assertTrue(
            WorkflowExecutionService.within_send_window(self.workflow, self._at(11))
        )

    def test_the_middle_of_the_night_is_not(self):
        self.assertFalse(
            WorkflowExecutionService.within_send_window(self.workflow, self._at(3))
        )

    def test_a_workflow_without_quiet_hours_sends_whenever(self):
        self.workflow.respect_quiet_hours = False
        self.assertTrue(
            WorkflowExecutionService.within_send_window(self.workflow, self._at(3))
        )

    def test_a_day_not_chosen_is_refused(self):
        self.workflow.send_weekdays = [0, 1, 2, 3, 4]  # weekdays only
        self.workflow.save(update_fields=['send_weekdays'])

        saturday = self._at(11, weekday=5)
        self.assertFalse(
            WorkflowExecutionService.within_send_window(self.workflow, saturday)
        )

    def test_an_empty_day_list_means_every_day(self):
        saturday = self._at(11, weekday=5)
        self.assertTrue(
            WorkflowExecutionService.within_send_window(self.workflow, saturday)
        )

    def test_a_window_that_wraps_past_midnight_works(self):
        self.workflow.send_window_start = time(22, 0)
        self.workflow.send_window_end = time(6, 0)
        self.workflow.save()

        self.assertTrue(
            WorkflowExecutionService.within_send_window(self.workflow, self._at(23))
        )
        self.assertTrue(
            WorkflowExecutionService.within_send_window(self.workflow, self._at(2))
        )
        self.assertFalse(
            WorkflowExecutionService.within_send_window(self.workflow, self._at(12))
        )

    def test_the_next_slot_lands_inside_the_window(self):
        slot = WorkflowExecutionService.next_send_slot(self.workflow, self._at(3))

        self.assertTrue(
            WorkflowExecutionService.within_send_window(self.workflow, slot)
        )
        self.assertGreater(slot, self._at(3))

    def test_a_time_already_inside_the_window_is_returned_unchanged(self):
        when = self._at(11)
        self.assertEqual(
            WorkflowExecutionService.next_send_slot(self.workflow, when), when
        )

    def test_an_email_due_at_3am_waits_rather_than_sending(self):
        """Nothing is dropped: the same step runs again in the window."""
        send = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.ACTION_SEND_EMAIL,
            config={'template_id': ''},
        )
        execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=self.contact, status='active',
            current_node=send,
        )

        with patch.object(
            WorkflowExecutionService, 'within_send_window', return_value=False,
        ):
            WorkflowExecutionService.execute_node(execution)

        execution.refresh_from_db()
        self.assertEqual(execution.status, 'waiting')
        self.assertIsNotNone(execution.resume_at)
        # The step was not consumed, so nothing was sent and nothing was lost.
        self.assertEqual(execution.current_node_id, send.id)
        self.assertEqual(execution.steps.count(), 0)

    def test_a_tag_step_is_not_held_back(self):
        """Delaying a tag changes what the workflow does, not its manners."""
        tag_node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.ACTION_ADD_TAG,
            config={'tag_id': ''},
        )
        self.assertNotIn(
            tag_node.node_type, WorkflowExecutionService.OUTBOUND_NODES,
        )


class GoalExitTests(EntryTestCase):
    def test_a_contact_who_meets_the_goal_leaves_the_workflow(self):
        self.workflow.exit_on_goal = True
        self.workflow.goal_rules = {
            'logic': 'all',
            'rules': [
                {'field': 'lifecycle_stage', 'operator': 'equals',
                 'value': 'customer'},
            ],
        }
        self.workflow.save()
        self.contact.lifecycle_stage = 'customer'
        self.contact.save(update_fields=['lifecycle_stage'])

        node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.ACTION_ADD_TAG,
            config={'tag_id': ''},
        )
        execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=self.contact, status='active',
            current_node=node,
        )

        WorkflowExecutionService.execute_node(execution)

        execution.refresh_from_db()
        self.assertEqual(execution.status, 'completed')
        self.assertTrue(execution.goal_reached)
        # It left before running the step, which is the point: nobody who has
        # already converted should be chased.
        self.assertEqual(execution.steps.count(), 0)

    def test_a_contact_who_does_not_meet_it_carries_on(self):
        self.workflow.goal_rules = {
            'logic': 'all',
            'rules': [
                {'field': 'lifecycle_stage', 'operator': 'equals',
                 'value': 'customer'},
            ],
        }
        self.workflow.save()

        execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=self.contact, status='active',
        )
        self.assertFalse(WorkflowExecutionService.goal_met(execution))

    def test_exit_on_goal_off_means_the_rules_are_not_consulted(self):
        self.workflow.exit_on_goal = False
        self.workflow.goal_rules = {
            'logic': 'all',
            'rules': [{'field': 'email', 'operator': 'is_not_empty', 'value': ''}],
        }
        self.workflow.save()

        execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=self.contact, status='active',
        )
        self.assertFalse(WorkflowExecutionService.goal_met(execution))

    def test_a_goal_is_only_counted_once(self):
        execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=self.contact, status='active',
        )
        WorkflowExecutionService._mark_goal_reached(execution)
        WorkflowExecutionService._mark_goal_reached(execution)

        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.contacts_goal_reached, 1)
