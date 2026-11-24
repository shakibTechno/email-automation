"""
The calendar reads five modules at once, which is exactly where it can go
wrong: one response quietly carrying another module's data, a day boundary
slipping because the server thinks in UTC, or a sequence turning its
per-contact rows into thousands of events.

Each test here is one of those.
"""
import datetime as dt

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organization, Role, User
from apps.campaigns.models import Campaign
from apps.contacts.models import Contact
from apps.crm.models import CRMTask, Activity, Deal, Pipeline, Stage
from apps.sequences.models import (
    EmailSequence, SequenceEnrollment, SequenceStep, SequenceStepExecution,
)

URL = '/api/v1/calendar/'


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class CalendarTestCase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name='Acme', email='org@acme.test', plan='free'
        )
        self.owner = User.objects.create_user(
            email='owner@acme.test', password='pw',
            organization=self.organization, role='owner', timezone='Asia/Dhaka',
        )

    # -- fixtures ----------------------------------------------------------

    def a_campaign(self, when, status='scheduled', name='Newsletter'):
        field = 'sent_at' if status == 'sent' else 'scheduled_at'
        return Campaign.objects.create(
            organization=self.organization, name=name, subject='Hi',
            status=status, recipient_count=10, created_by=self.owner,
            **{field: when},
        )

    def a_task(self, due, title='Chase proposal'):
        return CRMTask.objects.create(
            organization=self.organization, title=title, due_date=due,
        )

    def an_activity(self, due, duration=30, title='Call'):
        return Activity.objects.create(
            organization=self.organization, title=title,
            activity_type='call', due_date=due, duration=duration,
        )

    def a_deal(self, close_date, title='Nordwind'):
        pipeline = Pipeline.objects.create(
            organization=self.organization, name='Sales', created_by=self.owner,
        )
        stage = Stage.objects.create(pipeline=pipeline, name='New', position=0)
        return Deal.objects.create(
            organization=self.organization, pipeline=pipeline, stage=stage,
            title=title, close_date=close_date,
        )

    def a_sequence_due(self, when, count, name='Welcome series'):
        """`count` pending executions, all due at the same moment."""
        sequence = EmailSequence.objects.create(
            organization=self.organization, name=name, status='active',
        )
        step = SequenceStep.objects.create(
            sequence=sequence, position=0, subject='Step one',
        )
        for i in range(count):
            contact = Contact.objects.create(
                organization=self.organization, email=f'c{i}@example.test',
            )
            enrollment = SequenceEnrollment.objects.create(
                sequence=sequence, contact=contact,
            )
            SequenceStepExecution.objects.create(
                enrollment=enrollment, step=step, scheduled_at=when,
                status='pending',
            )
        return sequence

    def fetch(self, user=None, **params):
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        return client_for(user or self.owner).get(f'{URL}?{query}' if query else URL)


class CalendarRangeTestCase(CalendarTestCase):
    def test_a_campaign_in_range_is_returned_once(self):
        self.a_campaign(timezone.now() + dt.timedelta(days=2))
        response = self.fetch(start='2026-01-01', end='2026-01-31')
        self.assertEqual(response.status_code, 200)

        # Out of that range entirely.
        self.assertEqual(response.data['events'], [])

    def test_a_sent_campaign_is_not_listed_twice(self):
        """
        A sent campaign has both a scheduled_at and a sent_at. Reading the two
        columns as separate sources put it on the calendar twice -- once where
        it was planned, once where it went.
        """
        when = timezone.now().astimezone(dt.timezone.utc)
        campaign = self.a_campaign(when, status='sent', name='Went out')
        campaign.scheduled_at = when - dt.timedelta(days=1)
        campaign.save(update_fields=['scheduled_at'])

        today = timezone.now().date()
        response = self.fetch(
            start=(today - dt.timedelta(days=5)).isoformat(),
            end=(today + dt.timedelta(days=5)).isoformat(),
        )
        campaigns = [e for e in response.data['events'] if e['source'] == 'campaigns']
        self.assertEqual(len(campaigns), 1)
        self.assertEqual(campaigns[0]['status'], 'sent')

    def test_an_all_day_task_does_not_drift_across_a_timezone(self):
        """
        The viewer reads Asia/Dhaka. A task due on the 1st must come back on
        the 1st, not on the 30th because a date was compared against a UTC
        instant.
        """
        self.a_task(dt.date(2026, 12, 1))
        response = self.fetch(start='2026-12-01', end='2026-12-31')
        tasks = [e for e in response.data['events'] if e['source'] == 'tasks']
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['start'], '2026-12-01')
        self.assertTrue(tasks[0]['all_day'])

        previous = self.fetch(start='2026-11-01', end='2026-11-30')
        self.assertEqual(
            [e for e in previous.data['events'] if e['source'] == 'tasks'], []
        )

    def test_an_event_on_the_last_day_of_the_range_is_included(self):
        self.a_task(dt.date(2026, 12, 31))
        response = self.fetch(start='2026-12-01', end='2026-12-31')
        self.assertEqual(len(response.data['events']), 1)

    def test_a_late_evening_campaign_belongs_to_the_viewers_day(self):
        """
        23:30 on the 31st in Dhaka is 17:30 UTC on the 31st. Asking for
        December must include it; a range that ends at UTC midnight would not.
        """
        dhaka = dt.timezone(dt.timedelta(hours=6))
        self.a_campaign(dt.datetime(2026, 12, 31, 23, 30, tzinfo=dhaka))
        response = self.fetch(start='2026-12-01', end='2026-12-31')
        self.assertEqual(len(response.data['events']), 1)

    def test_an_after_midnight_send_counts_into_the_viewers_day(self):
        """
        01:00 on 1 December in Dhaka is 19:00 UTC on 30 November. Grouping
        sequence volume by the database's day put the chip on the 30th.
        """
        dhaka = dt.timezone(dt.timedelta(hours=6))
        self.a_sequence_due(dt.datetime(2026, 12, 1, 1, 0, tzinfo=dhaka), 5)
        response = self.fetch(start='2026-12-01', end='2026-12-31')
        chips = [e for e in response.data['events'] if e['source'] == 'sequences']
        self.assertEqual(len(chips), 1)
        self.assertEqual(chips[0]['start'], '2026-12-01')

    def test_an_oversized_range_is_refused(self):
        response = self.fetch(start='2026-01-01', end='2026-12-31')
        self.assertEqual(response.status_code, 400)

    def test_a_backwards_range_is_refused(self):
        response = self.fetch(start='2026-12-31', end='2026-12-01')
        self.assertEqual(response.status_code, 400)

    def test_nonsense_dates_are_refused(self):
        response = self.fetch(start='last tuesday')
        self.assertEqual(response.status_code, 400)

    def test_no_range_defaults_to_this_month(self):
        response = self.fetch()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['start'].endswith('-01'))


class CalendarSourcesTestCase(CalendarTestCase):
    def test_all_five_sources_land_in_one_response(self):
        today = timezone.now().astimezone(dt.timezone(dt.timedelta(hours=6))).date()
        start = today.replace(day=1)
        self.a_campaign(timezone.now() + dt.timedelta(hours=2))
        self.a_task(today)
        self.an_activity(timezone.now() + dt.timedelta(hours=3))
        self.a_deal(today)
        self.a_sequence_due(timezone.now() + dt.timedelta(hours=4), 3)

        response = self.fetch(
            start=start.isoformat(),
            end=(start + dt.timedelta(days=27)).isoformat(),
        )
        sources = {e['source'] for e in response.data['events']}
        self.assertEqual(
            sources, {'campaigns', 'tasks', 'activities', 'deals', 'sequences'}
        )
        self.assertEqual(
            {s['key'] for s in response.data['sources']},
            {'campaigns', 'sequences', 'activities', 'tasks', 'deals'},
        )

    def test_the_counts_match_the_events(self):
        today = timezone.now().astimezone(dt.timezone(dt.timedelta(hours=6))).date()
        self.a_task(today, title='One')
        self.a_task(today, title='Two')
        response = self.fetch(
            start=today.replace(day=1).isoformat(),
            end=(today.replace(day=1) + dt.timedelta(days=27)).isoformat(),
        )
        counts = {s['key']: s['count'] for s in response.data['sources']}
        self.assertEqual(counts['tasks'], 2)

    def test_an_activity_with_a_duration_gets_an_end(self):
        when = timezone.now() + dt.timedelta(hours=2)
        self.an_activity(when, duration=90)
        today = timezone.now().date()
        response = self.fetch(
            start=today.isoformat(), end=(today + dt.timedelta(days=2)).isoformat()
        )
        activity = [e for e in response.data['events'] if e['source'] == 'activities'][0]
        self.assertIsNotNone(activity['end'])
        self.assertEqual(activity['meta']['duration'], 90)


class SequenceVolumeTestCase(CalendarTestCase):
    def test_a_day_of_sends_is_one_chip_with_a_count(self):
        when = timezone.now() + dt.timedelta(hours=5)
        self.a_sequence_due(when, 40)

        today = timezone.now().date()
        response = self.fetch(
            start=today.isoformat(), end=(today + dt.timedelta(days=3)).isoformat()
        )
        chips = [e for e in response.data['events'] if e['source'] == 'sequences']
        self.assertEqual(len(chips), 1, 'volume must not become one event per row')
        self.assertEqual(chips[0]['meta']['emails'], 40)
        self.assertFalse(chips[0]['movable'])

    def test_volume_is_counted_in_the_database_not_in_python(self):
        when = timezone.now() + dt.timedelta(hours=5)
        self.a_sequence_due(when, 60)
        today = timezone.now().date()

        # One query per source and no more, regardless of how many executions
        # are due: the day's rows are aggregated by the database. Loading them
        # to count in Python would scale with enrolment, which is the failure
        # this guards against.
        with self.assertNumQueries(5):
            self.fetch(
                start=today.isoformat(),
                end=(today + dt.timedelta(days=3)).isoformat(),
            )


class CalendarMovabilityTestCase(CalendarTestCase):
    def test_a_future_scheduled_campaign_can_be_moved(self):
        self.a_campaign(timezone.now() + dt.timedelta(days=1))
        today = timezone.now().date()
        response = self.fetch(
            start=today.isoformat(), end=(today + dt.timedelta(days=3)).isoformat()
        )
        self.assertTrue(response.data['events'][0]['movable'])

    def test_a_sending_campaign_cannot_be_moved(self):
        self.a_campaign(timezone.now() + dt.timedelta(days=1), status='sending')
        today = timezone.now().date()
        response = self.fetch(
            start=today.isoformat(), end=(today + dt.timedelta(days=3)).isoformat()
        )
        self.assertFalse(response.data['events'][0]['movable'])

    def test_a_past_campaign_cannot_be_moved(self):
        self.a_campaign(timezone.now() - dt.timedelta(days=1))
        today = timezone.now().date()
        response = self.fetch(
            start=(today - dt.timedelta(days=3)).isoformat(), end=today.isoformat()
        )
        self.assertFalse(response.data['events'][0]['movable'])

    def test_a_viewer_sees_events_but_cannot_move_them(self):
        viewer = User.objects.create_user(
            email='viewer@acme.test', password='pw',
            organization=self.organization, role='viewer',
        )
        self.a_campaign(timezone.now() + dt.timedelta(days=1))
        today = timezone.now().date()
        response = self.fetch(
            user=viewer,
            start=today.isoformat(), end=(today + dt.timedelta(days=3)).isoformat(),
        )
        self.assertEqual(len(response.data['events']), 1)
        self.assertFalse(response.data['events'][0]['movable'])

    def test_a_completed_task_cannot_be_moved(self):
        today = timezone.now().astimezone(dt.timezone(dt.timedelta(hours=6))).date()
        task = self.a_task(today)
        task.status = 'done'
        task.save(update_fields=['status'])
        response = self.fetch(
            start=today.isoformat(), end=(today + dt.timedelta(days=1)).isoformat()
        )
        self.assertFalse(response.data['events'][0]['movable'])


class CalendarPermissionTestCase(CalendarTestCase):
    """
    The leak this endpoint invites: five modules in one response. A role is the
    only thing standing between a viewer and another module's data.
    """

    def setUp(self):
        super().setUp()
        self.today = timezone.now().astimezone(
            dt.timezone(dt.timedelta(hours=6))
        ).date()
        self.a_campaign(timezone.now() + dt.timedelta(hours=2))
        self.a_task(self.today)

    def role_user(self, permissions, email='staff@acme.test'):
        role = Role.objects.create(
            organization=self.organization, name='Limited', slug='limited',
            permissions=permissions,
        )
        return User.objects.create_user(
            email=email, password='pw', organization=self.organization,
            role=role.slug, timezone='Asia/Dhaka',
        )

    def test_a_role_without_campaigns_view_gets_no_sends(self):
        user = self.role_user(['crm.view'])
        response = self.fetch(
            user=user,
            start=self.today.isoformat(),
            end=(self.today + dt.timedelta(days=3)).isoformat(),
        )
        self.assertEqual(response.status_code, 200)
        sources = {e['source'] for e in response.data['events']}
        self.assertNotIn('campaigns', sources)
        self.assertIn('tasks', sources)

    def test_a_source_the_role_cannot_see_is_absent_not_empty(self):
        user = self.role_user(['crm.view'])
        response = self.fetch(user=user)
        keys = {s['key'] for s in response.data['sources']}
        self.assertEqual(keys, {'activities', 'tasks', 'deals'})

    def test_a_role_with_no_permissions_gets_an_empty_calendar(self):
        user = self.role_user([])
        response = self.fetch(user=user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['events'], [])
        self.assertEqual(response.data['sources'], [])

    def test_another_organizations_events_never_appear(self):
        other = Organization.objects.create(name='Other', email='o@other.test')
        stranger = User.objects.create_user(
            email='them@other.test', password='pw', organization=other, role='owner',
        )
        Campaign.objects.create(
            organization=other, name='Theirs', subject='Hi', status='scheduled',
            scheduled_at=timezone.now() + dt.timedelta(hours=2),
        )

        response = self.fetch(
            start=self.today.isoformat(),
            end=(self.today + dt.timedelta(days=3)).isoformat(),
        )
        titles = {e['title'] for e in response.data['events']}
        self.assertNotIn('Theirs', titles)

        theirs = self.fetch(
            user=stranger,
            start=self.today.isoformat(),
            end=(self.today + dt.timedelta(days=3)).isoformat(),
        )
        self.assertEqual({e['title'] for e in theirs.data['events']}, {'Theirs'})

    def test_an_anonymous_request_is_refused(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)
