"""
The dashboard reads six modules into one response, which is where it can leak:
a viewer learning the organization's billing state from a page they opened for
a chart. Most of what follows is about who sees which block.

The rest is about the two things a dashboard has to get right: an alert that
only appears when something is actually wrong, and rates rather than running
totals.
"""
import datetime as dt

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organization, Role, User
from apps.billing.models import Plan, Subscription
from apps.campaigns.models import Campaign
from apps.contacts.models import Contact
from apps.crm.models import Activity, CRMTask, Deal, Pipeline, Stage
from apps.email_config.models import EmailConfiguration, SendingDomain

URL = '/api/v1/dashboard/'


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class DashboardTestCase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name='Acme', email='org@acme.test', plan='free'
        )
        self.owner = User.objects.create_user(
            email='owner@acme.test', password='pw',
            organization=self.organization, role='owner', timezone='Asia/Dhaka',
        )

    def fetch(self, user=None, **params):
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        return client_for(user or self.owner).get(f'{URL}?{query}' if query else URL)

    def role_user(self, permissions, email='staff@acme.test', slug='limited'):
        role = Role.objects.create(
            organization=self.organization, name=slug.title(), slug=slug,
            permissions=permissions,
        )
        return User.objects.create_user(
            email=email, password='pw', organization=self.organization,
            role=role.slug, timezone='Asia/Dhaka',
        )

    def a_task(self, **kwargs):
        kwargs.setdefault('title', 'Chase proposal')
        return CRMTask.objects.create(organization=self.organization, **kwargs)


class DashboardShapeTestCase(DashboardTestCase):
    def test_an_owner_gets_every_block(self):
        response = self.fetch()
        self.assertEqual(response.status_code, 200)
        for key in ('alerts', 'tiles', 'upcoming', 'assigned',
                    'recent_campaigns', 'recent_submissions'):
            self.assertIn(key, response.data)

    def test_the_period_is_clamped(self):
        self.assertEqual(self.fetch(days=9000).data['days'], 90)
        self.assertEqual(self.fetch(days=0).data['days'], 1)
        self.assertEqual(self.fetch(days='nonsense').data['days'], 30)

    def test_an_anonymous_request_is_refused(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)


class DashboardAlertsTestCase(DashboardTestCase):
    def test_a_healthy_organization_has_no_alerts(self):
        """The card is absent, which is the whole point of it being credible."""
        self.assertEqual(self.fetch().data['alerts'], [])

    def test_paused_sending_is_an_alert(self):
        EmailConfiguration.objects.create(
            organization=self.organization,
            sending_paused_due_to_threshold=True,
            sending_paused_at=timezone.now(),
        )
        alerts = self.fetch().data['alerts']
        self.assertEqual([a['id'] for a in alerts], ['sending-paused'])
        self.assertEqual(alerts[0]['level'], 'action')

    def test_an_unverified_domain_is_an_alert(self):
        SendingDomain.objects.create(
            organization=self.organization, domain='mail.acme.test',
            status=SendingDomain.STATUS_PENDING,
        )
        ids = [a['id'] for a in self.fetch().data['alerts']]
        self.assertEqual(len(ids), 1)
        self.assertTrue(ids[0].startswith('domain-'))

    def test_a_verified_domain_is_not(self):
        SendingDomain.objects.create(
            organization=self.organization, domain='mail.acme.test',
            status=SendingDomain.STATUS_VERIFIED,
        )
        self.assertEqual(self.fetch().data['alerts'], [])

    def test_quota_warns_before_it_runs_out_and_escalates_after(self):
        plan = Plan.objects.create(
            name='Starter', plan_type='starter', max_emails_per_month=1000,
        )
        subscription = Subscription.objects.create(
            organization=self.organization, plan=plan, status='active',
            emails_sent_this_month=850,
        )
        alert = [a for a in self.fetch().data['alerts'] if a['id'] == 'quota'][0]
        self.assertEqual(alert['level'], 'soon')

        subscription.emails_sent_this_month = 1000
        subscription.save(update_fields=['emails_sent_this_month'])
        alert = [a for a in self.fetch().data['alerts'] if a['id'] == 'quota'][0]
        self.assertEqual(alert['level'], 'action')

    def test_plenty_of_quota_left_says_nothing(self):
        plan = Plan.objects.create(
            name='Starter', plan_type='starter', max_emails_per_month=1000,
        )
        Subscription.objects.create(
            organization=self.organization, plan=plan, status='active',
            emails_sent_this_month=100,
        )
        self.assertEqual(
            [a for a in self.fetch().data['alerts'] if a['id'] == 'quota'], []
        )

    def test_a_campaign_stuck_mid_send_is_an_alert(self):
        campaign = Campaign.objects.create(
            organization=self.organization, name='Black Friday', subject='Hi',
            status='sending', created_by=self.owner,
        )
        Campaign.objects.filter(pk=campaign.pk).update(
            updated_at=timezone.now() - dt.timedelta(hours=9)
        )
        alerts = self.fetch().data['alerts']
        self.assertEqual([a['title'] for a in alerts], ['Campaign stuck mid-send'])

    def test_a_campaign_that_just_started_sending_is_not(self):
        Campaign.objects.create(
            organization=self.organization, name='Black Friday', subject='Hi',
            status='sending', created_by=self.owner,
        )
        self.assertEqual(self.fetch().data['alerts'], [])

    def test_urgent_alerts_come_first(self):
        EmailConfiguration.objects.create(
            organization=self.organization,
            sending_paused_due_to_threshold=True,
        )
        plan = Plan.objects.create(
            name='Starter', plan_type='starter', max_emails_per_month=1000,
        )
        Subscription.objects.create(
            organization=self.organization, plan=plan, status='active',
            emails_sent_this_month=850,
        )
        levels = [a['level'] for a in self.fetch().data['alerts']]
        self.assertEqual(levels, ['action', 'soon'])


class AssignedToMeTestCase(DashboardTestCase):
    def test_only_my_work_appears(self):
        colleague = User.objects.create_user(
            email='them@acme.test', password='pw',
            organization=self.organization, role='member',
        )
        self.a_task(title='Mine', assigned_to=self.owner)
        self.a_task(title='Theirs', assigned_to=colleague)
        self.a_task(title='Nobody')

        titles = [i['title'] for i in self.fetch().data['assigned']['items']]
        self.assertEqual(titles, ['Mine'])

    def test_overdue_first_then_today_then_later(self):
        today = timezone.now().date()
        self.a_task(title='Later', assigned_to=self.owner,
                    due_date=today + dt.timedelta(days=4))
        self.a_task(title='Today', assigned_to=self.owner, due_date=today)
        self.a_task(title='Late', assigned_to=self.owner,
                    due_date=today - dt.timedelta(days=2))

        titles = [i['title'] for i in self.fetch().data['assigned']['items']]
        self.assertEqual(titles, ['Late', 'Today', 'Later'])

    def test_undated_work_sorts_last_rather_than_first(self):
        today = timezone.now().date()
        self.a_task(title='No date', assigned_to=self.owner)
        self.a_task(title='Today', assigned_to=self.owner, due_date=today)

        titles = [i['title'] for i in self.fetch().data['assigned']['items']]
        self.assertEqual(titles, ['Today', 'No date'])

    def test_a_finished_task_is_gone(self):
        self.a_task(title='Done already', assigned_to=self.owner, status='done')
        self.assertEqual(self.fetch().data['assigned']['items'], [])

    def test_calls_booked_for_me_sit_beside_my_tasks(self):
        Activity.objects.create(
            organization=self.organization, title='Call — Rivo',
            activity_type='call', assigned_to=self.owner,
            due_date=timezone.now() + dt.timedelta(hours=3),
        )
        self.a_task(title='A task', assigned_to=self.owner,
                    due_date=timezone.now().date() + dt.timedelta(days=5))
        titles = [i['title'] for i in self.fetch().data['assigned']['items']]
        self.assertEqual(titles, ['Call — Rivo', 'A task'])

    def test_newly_assigned_work_is_counted(self):
        self.a_task(title='Fresh', assigned_to=self.owner)
        old = self.a_task(title='Old', assigned_to=self.owner)
        CRMTask.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - dt.timedelta(days=3)
        )
        assigned = self.fetch().data['assigned']
        self.assertEqual(assigned['new_count'], 1)

    def test_the_overflow_is_counted_not_listed(self):
        today = timezone.now().date()
        for i in range(7):
            self.a_task(title=f'Task {i}', assigned_to=self.owner,
                        due_date=today + dt.timedelta(days=i))
        assigned = self.fetch().data['assigned']
        self.assertEqual(len(assigned['items']), 4)
        self.assertEqual(assigned['more'], 3)


class DashboardTilesTestCase(DashboardTestCase):
    def test_every_tile_is_a_rate_not_a_running_total(self):
        keys = {t['key'] for t in self.fetch().data['tiles']}
        self.assertEqual(keys, {'deliverability', 'engagement', 'audience', 'conversion'})

    def test_net_audience_falls_when_people_leave(self):
        for i in range(5):
            Contact.objects.create(
                organization=self.organization, email=f'c{i}@example.test'
            )
        Contact.objects.filter(email='c0@example.test').update(
            unsubscribed_at=timezone.now()
        )
        Contact.objects.filter(email='c1@example.test').update(
            unsubscribed_at=timezone.now()
        )

        tile = [t for t in self.fetch().data['tiles'] if t['key'] == 'audience'][0]
        self.assertEqual(tile['value'], 3)
        self.assertIn('2 unsubscribed', tile['sub'])

    def test_an_empty_organization_does_not_divide_by_zero(self):
        tiles = {t['key']: t for t in self.fetch().data['tiles']}
        self.assertEqual(tiles['deliverability']['value'], 0)
        self.assertEqual(tiles['conversion']['value'], 0)
        self.assertIsNone(tiles['engagement']['delta'])


class DashboardPermissionTestCase(DashboardTestCase):
    """
    One response, six modules. Each block has to answer to its own permission.
    """

    def setUp(self):
        super().setUp()
        EmailConfiguration.objects.create(
            organization=self.organization,
            sending_paused_due_to_threshold=True,
        )
        self.a_task(title='A task', assigned_to=self.owner)

    def test_a_role_without_billing_is_not_told_about_billing(self):
        plan = Plan.objects.create(
            name='Starter', plan_type='starter', max_emails_per_month=1000,
        )
        Subscription.objects.create(
            organization=self.organization, plan=plan, status='active',
            emails_sent_this_month=990,
        )
        user = self.role_user(['campaigns.view'])
        ids = [a['id'] for a in self.fetch(user=user).data['alerts']]
        self.assertNotIn('quota', ids)

    def test_a_role_without_email_config_is_not_told_sending_is_paused(self):
        user = self.role_user(['campaigns.view'])
        ids = [a['id'] for a in self.fetch(user=user).data['alerts']]
        self.assertNotIn('sending-paused', ids)

    def test_assigned_work_needs_crm_view(self):
        user = self.role_user(['campaigns.view'])
        self.assertNotIn('assigned', self.fetch(user=user).data)

    def test_the_lists_follow_their_own_permissions(self):
        user = self.role_user(['campaigns.view'])
        data = self.fetch(user=user).data
        self.assertIn('recent_campaigns', data)
        self.assertNotIn('recent_submissions', data)

    def test_tiles_are_dropped_with_the_module_they_read(self):
        user = self.role_user(['campaigns.view'])
        keys = {t['key'] for t in self.fetch(user=user).data['tiles']}
        self.assertEqual(keys, {'deliverability', 'engagement'})

    def test_a_role_with_nothing_gets_an_empty_page_not_a_refusal(self):
        user = self.role_user([], email='nobody@acme.test', slug='nobody')
        response = self.fetch(user=user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['alerts'], [])
        self.assertEqual(response.data['tiles'], [])
        self.assertIsNone(response.data['upcoming'])
        self.assertNotIn('assigned', response.data)

    def test_another_organizations_work_never_appears(self):
        other = Organization.objects.create(name='Other', email='o@other.test')
        stranger = User.objects.create_user(
            email='them@other.test', password='pw', organization=other, role='owner',
        )
        CRMTask.objects.create(
            organization=other, title='Theirs', assigned_to=stranger,
        )
        titles = [i['title'] for i in self.fetch().data['assigned']['items']]
        self.assertEqual(titles, ['A task'])


class UpcomingTestCase(DashboardTestCase):
    def test_the_next_week_comes_from_the_calendar(self):
        pipeline = Pipeline.objects.create(
            organization=self.organization, name='Sales', created_by=self.owner,
        )
        stage = Stage.objects.create(pipeline=pipeline, name='New', position=0)
        Deal.objects.create(
            organization=self.organization, pipeline=pipeline, stage=stage,
            title='Nordwind', close_date=timezone.now().date() + dt.timedelta(days=2),
        )

        upcoming = self.fetch().data['upcoming']
        self.assertEqual(len(upcoming['days']), 7)
        self.assertEqual(upcoming['total'], 1)
        listed = [i for day in upcoming['days'] for i in day['items']]
        self.assertEqual(listed[0]['kind'], 'deals')
