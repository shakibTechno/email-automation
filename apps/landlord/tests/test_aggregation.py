"""
Cross-tenant aggregation: correctness and cost.

Cost matters as much as correctness here. These endpoints read every tenant, so
anything that scales per tenant is fine with one customer and unusable with a
thousand — and that is exactly the kind of regression nobody notices until it is
expensive to fix.
"""
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.billing.models import Subscription
from apps.billing.testing import create_plans
from apps.campaigns.models import Campaign, CampaignRecipient
from apps.contacts.models import Contact
from apps.email_config.models import EmailConfiguration, PostalTenant
from apps.landlord.services import (
    DeliverabilityService,
    PlatformOverviewService,
    RevenueService,
    TenantService,
)


class AggregationTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        create_plans()
        self.staff = User.objects.create_user(
            email='ops@platform.test', password='x', organization=None, is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.staff)

    def _tenant(self, name, plan='free', bounce_rate=0, held=0):
        org = Organization.objects.create(name=name, slug=name.lower(), plan=plan)
        PostalTenant.objects.create(
            organization=org, external_id=f'{name.lower()}-0001',
            postal_tenant_id=f'pt-{name.lower()}', api_key='k',
            bounce_rate_30d=bounce_rate, held=held,
        )
        EmailConfiguration.objects.create(organization=org, bounce_threshold_pct=5)
        return org

    # -------------------------------------------------------------- overview
    def test_overview_counts_tenants_and_suspensions(self):
        self._tenant('Alpha')
        suspended = self._tenant('Beta')
        suspended.is_active = False
        suspended.save(update_fields=['is_active'])

        data = PlatformOverviewService.get_overview(use_cache=False)

        self.assertEqual(data['tenants']['total'], 2)
        self.assertEqual(data['tenants']['active'], 1)
        self.assertEqual(data['tenants']['suspended'], 1)

    def test_overview_excludes_platform_staff_from_the_user_count(self):
        """Operators are not customers and must not inflate the figure."""
        org = self._tenant('Alpha')
        User.objects.create_user(email='a@alpha.test', password='x', organization=org)

        self.assertEqual(PlatformOverviewService.get_overview(use_cache=False)['users'], 1)

    def test_signup_series_is_dense(self):
        """Days with no signups appear as zero — a sparse series draws wrong."""
        self._tenant('Alpha')
        series = PlatformOverviewService.get_overview(days=7, use_cache=False)['signups_by_day']

        self.assertEqual(len(series), 8)  # inclusive of both endpoints
        self.assertTrue(all('date' in p and 'count' in p for p in series))

    def test_overview_is_cached(self):
        self._tenant('Alpha')
        first = PlatformOverviewService.get_overview()
        self._tenant('Beta')

        self.assertEqual(PlatformOverviewService.get_overview()['tenants']['total'],
                         first['tenants']['total'],
                         'the cached value should be served')
        self.assertEqual(PlatformOverviewService.get_overview(use_cache=False)['tenants']['total'], 2)

    # ---------------------------------------------------------------- tenants
    def test_tenant_list_does_not_scale_queries_with_tenant_count(self):
        """
        The guard against a per-row lookup creeping in.

        Asserts the query count is *constant*, not a particular number — the
        number is an implementation detail, but anything querying inside the
        serialization loop would make it grow with tenants, and that is the
        regression worth catching. Serializing is included because the cost
        hides there, not in building the queryset.
        """
        def queries_for(page_size=25):
            with CaptureQueriesContext(connection) as ctx:
                rows = TenantService.base_queryset()[:page_size]
                [TenantService.serialize_row(o) for o in rows]
            return len(ctx)

        for i in range(3):
            self._tenant(f'Small{i}')
        with_three = queries_for()

        for i in range(7):
            self._tenant(f'More{i}')
        with_ten = queries_for()

        self.assertEqual(
            with_three, with_ten,
            f'queries grew from {with_three} to {with_ten} when tenants went '
            'from 3 to 10 — something is querying per row',
        )

    def test_tenant_row_separates_connected_domains_from_working_ones(self):
        """
        "Connected but not live" is the state an operator gets asked about, so a
        single count would hide the only number that matters.
        """
        from apps.landing_pages.models import LandingDomain

        org = self._tenant('Alpha')
        LandingDomain.objects.create(
            organization=org, domain='live.alpha-example.com',
            status=LandingDomain.STATUS_VERIFIED,
        )
        LandingDomain.objects.create(organization=org, domain='pending.alpha-example.com')

        row = TenantService.serialize_row(TenantService.base_queryset().get(pk=org.pk))

        self.assertEqual(row['landing_domains'], 2)
        self.assertEqual(row['landing_domains_unverified'], 1)

    def test_tenant_row_uses_cached_postal_metrics(self):
        org = self._tenant('Alpha', bounce_rate=7.5, held=3)
        row = TenantService.serialize_row(TenantService.base_queryset().get(pk=org.pk))

        self.assertEqual(row['bounce_rate_30d'], 7.5)
        self.assertEqual(row['held'], 3)

    def test_tenant_list_filters(self):
        self._tenant('Alpha', plan='free')
        self._tenant('Beta', plan='professional')

        self.assertEqual(
            self.api.get('/api/v1/landlord/tenants/?plan=professional').data['total'], 1)
        self.assertEqual(
            self.api.get('/api/v1/landlord/tenants/?search=alph').data['total'], 1)

    def test_tenant_detail_includes_live_deliverability(self):
        org = self._tenant('Alpha')
        response = self.api.get(f'/api/v1/landlord/tenants/{org.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('deliverability', response.data)
        self.assertIn('bounce_rate', response.data['deliverability'])
        self.assertIn('domains', response.data)
        # `users` is the count on both the row and the detail; the people are
        # `members`. If these ever swap, the console renders an array as a
        # figure and the list silently disappears.
        self.assertIsInstance(response.data['users'], int)
        self.assertIsInstance(response.data['members'], list)

    # --------------------------------------------------------- deliverability
    def test_risk_board_ranks_the_worst_tenant_first(self):
        self._tenant('Clean', bounce_rate=0.5)
        self._tenant('Risky', bounce_rate=18.0)
        self._tenant('Middling', bounce_rate=2.0)

        board = DeliverabilityService.get_risk_board()

        self.assertEqual(board[0]['organization_name'], 'Risky')
        self.assertTrue(board[0]['over_threshold'])
        self.assertFalse(board[-1]['over_threshold'])

    def test_held_mail_raises_risk_even_below_the_bounce_threshold(self):
        """Held mail never moves again on its own — a tenant silently failing."""
        self._tenant('Quiet', bounce_rate=0.1, held=0)
        self._tenant('Stuck', bounce_rate=0.1, held=40)

        board = DeliverabilityService.get_risk_board()
        self.assertEqual(board[0]['organization_name'], 'Stuck')

    # ---------------------------------------------------------------- revenue
    def test_mrr_counts_only_active_and_trialing(self):
        paid = self._tenant('Paid', plan='professional')
        cancelled = self._tenant('Gone', plan='professional')

        Subscription.objects.filter(organization=cancelled).update(status='cancelled')
        sub = Subscription.objects.get(organization=paid)
        sub.status = 'active'
        sub.plan = sub.plan.__class__.objects.get(plan_type='professional', interval='month')
        sub.save()

        data = RevenueService.get_revenue()
        self.assertEqual(data['mrr'], 99.0)

    def test_trials_ending_soon_are_surfaced(self):
        org = self._tenant('Trial')
        Subscription.objects.filter(organization=org).update(
            status='trialing', trial_end=timezone.now() + timezone.timedelta(days=3),
        )

        names = [t['organization_name'] for t in RevenueService.get_revenue()['trials_ending']]
        self.assertIn('Trial', names)

    def test_tenants_near_their_quota_are_surfaced(self):
        org = self._tenant('Heavy')
        Subscription.objects.filter(organization=org).update(emails_sent_this_month=950)

        near = RevenueService.get_revenue()['near_quota']
        self.assertEqual(len(near), 1)
        self.assertGreaterEqual(near[0]['percent'], 80)
