"""
The dashboard and the campaign report must agree about what "delivered" means.

They did not. `status` is a single column that advances through a funnel, so a
recipient who opens a message no longer has status 'delivered'. The dashboard
counted `status='delivered'` alone and the campaign report OR-ed three statuses
together, so one campaign to two people — one of whom clicked — showed
2 delivered on the campaign page and 1 on the dashboard.
"""
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization, User
from apps.analytics.services import CampaignAnalyticsService
from apps.campaigns.models import Campaign, CampaignRecipient
from apps.contacts.models import Contact
from apps.core.services import DashboardService


class DeliveryMetricAgreementTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Metrics Co', slug='metrics-co')
        self.user = User.objects.create_user(
            email='owner@metrics.test', password='x', organization=self.org, role='owner',
        )
        self.campaign = Campaign.objects.create(
            organization=self.org, created_by=self.user, name='October',
            subject='October', status='sent', sent_at=timezone.now(),
        )

    def _recipient(self, email, **kwargs):
        contact = Contact.objects.create(organization=self.org, email=email)
        return CampaignRecipient.objects.create(
            campaign=self.campaign, contact=contact, email=email,
            sent_at=timezone.now(), **kwargs,
        )

    def test_dashboard_and_campaign_report_agree(self):
        """The exact shape that was reported: two sent, one went on to click."""
        now = timezone.now()
        self._recipient('plain@example.com', status='delivered', delivered_at=now)
        self._recipient(
            'engaged@example.com', status='clicked',
            delivered_at=now, opened_at=now, clicked_at=now,
        )

        dashboard = DashboardService.get_campaign_stats(self.org, days=30)
        report = CampaignAnalyticsService.get_campaign_detail(self.campaign)

        self.assertEqual(dashboard['emails_delivered'], 2)
        self.assertEqual(report['delivered'], 2)
        self.assertEqual(
            dashboard['emails_delivered'], report['delivered'],
            'the dashboard and the campaign report must not disagree',
        )

    def test_engagement_states_all_count_as_delivered(self):
        """
        Every state below is unreachable unless the message arrived — you
        cannot open, click or unsubscribe from mail that never landed.
        """
        now = timezone.now()
        for i, status in enumerate(CampaignRecipient.DELIVERED_STATUSES):
            self._recipient(f'r{i}@example.com', status=status)

        count = CampaignRecipient.objects.filter(
            CampaignRecipient.delivered_filter()
        ).count()
        self.assertEqual(count, len(CampaignRecipient.DELIVERED_STATUSES))

    def test_a_delivery_timestamp_counts_even_without_a_matching_status(self):
        """
        A provider webhook sets delivered_at. The status may since have moved
        on, or never have been updated at all — the timestamp still proves it.
        """
        self._recipient('ts@example.com', status='sent', delivered_at=timezone.now())

        self.assertEqual(
            CampaignRecipient.objects.filter(CampaignRecipient.delivered_filter()).count(), 1
        )

    def test_sent_but_unconfirmed_is_not_delivered(self):
        """Handed to the provider is not the same as arrived."""
        self._recipient('pending@example.com', status='sent')

        self.assertEqual(
            CampaignRecipient.objects.filter(CampaignRecipient.delivered_filter()).count(), 0
        )

    def test_bounced_is_not_delivered(self):
        self._recipient('bad@example.com', status='bounced', bounced_at=timezone.now())

        self.assertEqual(
            CampaignRecipient.objects.filter(CampaignRecipient.delivered_filter()).count(), 0
        )
        self.assertEqual(
            CampaignRecipient.objects.filter(CampaignRecipient.bounced_filter()).count(), 1
        )
