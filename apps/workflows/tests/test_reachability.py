"""
A node nothing leads to is never run, and the run that walks past it finishes
as `completed` with no error anywhere.

That is not hypothetical: an active workflow sent its intro email, added its
tag and stopped one edge short of the condition leading to its goal. Both runs
read "Completed" on the detail page, one with the goal reached and one without,
and nothing said why.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.workflows import reachability
from apps.workflows.models import Workflow, WorkflowEdge, WorkflowNode


class ReachabilityTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.workflow = Workflow.objects.create(
            organization=self.org, name='NewWorkflow', status='active',
        )

    def node(self, node_type, label='', **config):
        return WorkflowNode.objects.create(
            workflow=self.workflow, node_type=node_type, label=label,
            position_x=0, position_y=0, config=config,
        )

    def edge(self, source, target, handle='default'):
        return WorkflowEdge.objects.create(
            workflow=self.workflow, source_node=source, target_node=target,
            source_handle=handle,
        )

    def codes(self):
        return [p['code'] for p in reachability.problems(self.workflow)]


class ConnectedWorkflowTests(ReachabilityTestCase):
    def test_a_fully_connected_workflow_has_nothing_to_report(self):
        trigger = self.node(WorkflowNode.TRIGGER_CONTACT_CREATED, 'New contact')
        send = self.node(WorkflowNode.ACTION_SEND_EMAIL, 'Intro')
        goal = self.node('action_goal', 'Goal')
        self.edge(trigger, send)
        self.edge(send, goal)

        self.assertEqual(reachability.problems(self.workflow), [])

    def test_both_sides_of_a_condition_count_as_reached(self):
        trigger = self.node(WorkflowNode.TRIGGER_CONTACT_CREATED)
        branch = self.node('condition_if_else', 'If / Else')
        yes = self.node(WorkflowNode.ACTION_ADD_TAG, 'Tag A')
        no = self.node(WorkflowNode.ACTION_ADD_TAG, 'Tag B')
        goal = self.node('action_goal', 'Goal')
        self.edge(trigger, branch)
        self.edge(branch, yes, 'true')
        self.edge(branch, no, 'false')
        self.edge(yes, goal)
        self.edge(no, goal)

        self.assertEqual(reachability.problems(self.workflow), [])

    def test_a_branch_that_simply_stops_is_not_a_problem(self):
        """Plenty of paths end without a goal. Only unreachable is wrong."""
        trigger = self.node(WorkflowNode.TRIGGER_CONTACT_CREATED)
        tag = self.node(WorkflowNode.ACTION_ADD_TAG, 'Tag')
        self.edge(trigger, tag)

        self.assertEqual(reachability.problems(self.workflow), [])

    def test_an_empty_canvas_is_not_reported(self):
        self.assertEqual(reachability.problems(self.workflow), [])


class BrokenWorkflowTests(ReachabilityTestCase):
    def build_the_real_one(self):
        """
        The shape that shipped: the chain ends at Add Tag, and the condition,
        its branches and the goal are left floating.
        """
        trigger = self.node('trigger_form_submission', 'Fitst Inquiry')
        send = self.node(WorkflowNode.ACTION_SEND_EMAIL, 'Intro Email')
        tag = self.node(WorkflowNode.ACTION_ADD_TAG, 'Add Tag')
        branch = self.node('condition_if_else', 'If / Else')
        assign = self.node('action_assign_contact', 'Assign Owner')
        tag_yes = self.node(WorkflowNode.ACTION_ADD_TAG, 'Tag Ireland')
        tag_no = self.node(WorkflowNode.ACTION_ADD_TAG, 'Tag Other')
        goal = self.node('action_goal', 'Goal')

        self.edge(trigger, send)
        self.edge(send, tag)
        # The edge that is missing: tag -> branch.
        self.edge(branch, assign, 'true')
        self.edge(assign, tag_yes)
        self.edge(tag_yes, goal)
        self.edge(branch, tag_no, 'false')
        self.edge(tag_no, goal)
        return {'branch': branch, 'goal': goal, 'tag': tag}

    def test_the_orphaned_half_is_reported(self):
        nodes = self.build_the_real_one()
        found = {p['code']: p for p in reachability.problems(self.workflow)}

        self.assertIn('unreachable', found)
        self.assertIn('goal_unreachable', found)

        stranded = found['unreachable']['node_ids']
        self.assertEqual(len(stranded), 5)
        self.assertIn(str(nodes['branch'].id), stranded)
        self.assertIn(str(nodes['goal'].id), stranded)
        # The part that does run is not accused of anything.
        self.assertNotIn(str(nodes['tag'].id), stranded)

    def test_the_message_counts_and_names_the_steps(self):
        self.build_the_real_one()
        message = [
            p for p in reachability.problems(self.workflow)
            if p['code'] == 'unreachable'
        ][0]['message']

        self.assertIn('5 steps', message)
        self.assertIn('If / Else', message)
        self.assertIn('and 1 more', message)

    def test_drawing_the_missing_edge_clears_it(self):
        nodes = self.build_the_real_one()
        self.edge(nodes['tag'], nodes['branch'])

        self.assertEqual(reachability.problems(self.workflow), [])

    def test_a_workflow_with_no_trigger_says_so_and_stops_there(self):
        send = self.node(WorkflowNode.ACTION_SEND_EMAIL, 'Intro')
        goal = self.node('action_goal', 'Goal')
        self.edge(send, goal)

        found = reachability.problems(self.workflow)
        self.assertEqual([p['code'] for p in found], ['no_trigger'])

    def test_one_reachable_goal_is_enough(self):
        """Two goals, one stranded: the goal is still reachable, so no alarm."""
        trigger = self.node(WorkflowNode.TRIGGER_CONTACT_CREATED)
        goal = self.node('action_goal', 'Goal')
        self.node('action_goal', 'Stray goal')
        self.edge(trigger, goal)

        self.assertEqual(self.codes(), ['unreachable'])


class ReachabilityApiTests(ReachabilityTestCase):
    def test_the_workflow_carries_its_problems(self):
        trigger = self.node('trigger_form_submission', 'Inquiry')
        send = self.node(WorkflowNode.ACTION_SEND_EMAIL, 'Intro Email')
        self.node('action_goal', 'Goal')
        self.edge(trigger, send)

        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.get(f'/api/v1/workflows/{self.workflow.id}/')

        self.assertEqual(response.status_code, 200)
        codes = [p['code'] for p in response.data['problems']]
        self.assertEqual(sorted(codes), ['goal_unreachable', 'unreachable'])

    def test_a_healthy_workflow_reports_an_empty_list(self):
        trigger = self.node(WorkflowNode.TRIGGER_CONTACT_CREATED)
        goal = self.node('action_goal', 'Goal')
        self.edge(trigger, goal)

        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.get(f'/api/v1/workflows/{self.workflow.id}/')

        self.assertEqual(response.data['problems'], [])

    def test_saving_a_workflow_answers_with_what_is_dangling(self):
        """
        The moment that matters: the response to the save that broke it.
        """
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.patch(
            f'/api/v1/workflows/{self.workflow.id}/',
            {
                'nodes': [
                    {'id': 'n1', 'node_type': 'trigger_contact_created',
                     'label': 'New contact', 'position_x': 0, 'position_y': 0,
                     'config': {}},
                    {'id': 'n2', 'node_type': 'action_goal', 'label': 'Goal',
                     'position_x': 0, 'position_y': 200, 'config': {}},
                ],
                'edges': [],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        codes = [p['code'] for p in response.data['problems']]
        self.assertIn('goal_unreachable', codes)
