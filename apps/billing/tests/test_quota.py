"""
Monthly email quota: subscription creation, enforcement and counting.

Three things were broken together. initialize_subscription() had no callers, so
no organization had a Subscription. increment_email_usage() had no callers, so
emails_sent_this_month was permanently 0. And check_usage_limit() was called
only by a read-only endpoint, so nothing was enforced anywhere.
"""
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.billing.models import Plan, Subscription
from apps.billing.services import BillingService
from apps.billing.testing import create_plans
from apps.campaigns.models import Campaign, CampaignRecipient
from apps.contacts.models import Contact


class SubscriptionOnCreateTestCase(TestCase):
    def setUp(self):
        create_plans()

    def test_a_new_organization_gets_a_free_subscription(self):
        org = Organization.objects.create(name='New Co', slug='new-co')

        sub = Subscription.objects.get(organization=org)
        self.assertEqual(sub.plan.plan_type, 'free')
        self.assertEqual(sub.status, 'trialing')
        self.assertIsNotNone(sub.trial_end)
        self.assertIsNotNone(sub.usage_reset_date)

    def test_the_organization_limits_are_mirrored_from_the_plan(self):
        org = Organization.objects.create(name='Mirror Co', slug='mirror-co')
        org.refresh_from_db()

        free = Plan.objects.get(plan_type='free', interval='month')
        self.assertEqual(org.max_emails_per_month, free.max_emails_per_month)
        self.assertEqual(org.plan, 'free')

    def test_initializing_twice_does_not_duplicate(self):
        org = Organization.objects.create(name='Twice Co', slug='twice-co')
        BillingService.initialize_subscription(org, org.email or '')

        self.assertEqual(Subscription.objects.filter(organization=org).count(), 1)

    def test_organization_creation_survives_a_billing_failure(self):
        """
        An organization that cannot be created is unrecoverable; one without a
        subscription can be repaired by the backfill. So billing failures are
        logged, not raised.
        """
        Plan.objects.all().delete()  # initialize_subscription returns None

        org = Organization.objects.create(name='Orphan Co', slug='orphan-co')

        self.assertTrue(Organization.objects.filter(pk=org.pk).exists())
        self.assertFalse(Subscription.objects.filter(organization=org).exists())


class QuotaCheckTestCase(TestCase):
    def setUp(self):
        create_plans()
        self.org = Organization.objects.create(name='Quota Co', slug='quota-co')
        self.sub = Subscription.objects.get(organization=self.org)

    def test_a_send_that_fits_is_allowed(self):
        allowed, quota = BillingService.check_email_quota(self.org, 100)
        self.assertTrue(allowed)
        self.assertEqual(quota['limit'], 1000)
        self.assertEqual(quota['remaining'], 1000)

    def test_a_send_that_does_not_fit_is_refused(self):
        self.sub.emails_sent_this_month = 900
        self.sub.save(update_fields=['emails_sent_this_month'])

        allowed, quota = BillingService.check_email_quota(self.org, 200)
        self.assertFalse(allowed)
        self.assertEqual(quota['remaining'], 100)

    def test_a_send_that_exactly_fills_the_quota_is_allowed(self):
        self.sub.emails_sent_this_month = 900
        self.sub.save(update_fields=['emails_sent_this_month'])

        self.assertTrue(BillingService.check_email_quota(self.org, 100)[0])
        self.assertFalse(BillingService.check_email_quota(self.org, 101)[0])

    def test_no_subscription_falls_back_rather_than_blocking(self):
        """
        check_usage_limit() answers 'No active subscription' here, which as a
        send gate would block any organization whose subscription creation
        failed. This falls back to the organization's mirrored limit instead.
        """
        Subscription.objects.filter(organization=self.org).delete()
        self.org.max_emails_per_month = 5000
        self.org.save(update_fields=['max_emails_per_month'])

        allowed, quota = BillingService.check_email_quota(self.org, 4000)
        self.assertTrue(allowed)
        self.assertEqual(quota['limit'], 5000)

    def test_a_zero_limit_means_unlimited(self):
        """Consistent with how max_automations and max_landing_pages are read."""
        self.sub.plan.max_emails_per_month = 0
        self.sub.plan.save(update_fields=['max_emails_per_month'])

        allowed, quota = BillingService.check_email_quota(self.org, 10_000_000)
        self.assertTrue(allowed)
        self.assertTrue(quota['unlimited'])

    def test_usage_increments(self):
        BillingService.increment_email_usage(self.org, 7)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.emails_sent_this_month, 7)


class CampaignPreflightTestCase(TestCase):
    """The quota is checked before anything is queued, not per batch."""

    def setUp(self):
        create_plans()
        self.org = Organization.objects.create(name='Send Co', slug='send-co')
        self.sub = Subscription.objects.get(organization=self.org)
        self.user = User.objects.create_user(
            email='owner@send.co', password='x', organization=self.org, role='owner',
        )
        for i in range(5):
            Contact.objects.create(organization=self.org, email=f'c{i}@test.co')

        # send/ validates the campaign is complete before anything else, so
        # it needs a template or it is rejected with a 400 that never reaches
        # the quota check.
        from apps.templates.models import EmailTemplate
        template = EmailTemplate.objects.create(
            organization=self.org, name='Blast template',
            subject='Blast', html_content='<p>Hello</p>',
        )
        self.campaign = Campaign.objects.create(
            organization=self.org, created_by=self.user, name='Blast',
            subject='Blast', sender_name='Send Co', sender_email='hi@send.co',
            status='draft', recipient_type='all', template=template,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def _send(self):
        return self.api.post(
            f'/api/v1/campaigns/{self.campaign.id}/send/', {'send_now': True}, format='json'
        )

    def test_a_campaign_over_quota_is_refused_before_any_recipient_is_created(self):
        self.sub.emails_sent_this_month = 998  # 2 left, 5 needed
        self.sub.save(update_fields=['emails_sent_this_month'])

        response = self._send()

        self.assertEqual(response.status_code, 402)
        self.assertIn('2', str(response.data['error']))
        self.assertEqual(response.data['required'], 5)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'draft', 'must not start sending')
        self.assertEqual(
            CampaignRecipient.objects.filter(campaign=self.campaign).count(), 0,
            'no recipient rows should exist for a refused campaign',
        )

    def test_the_refusal_names_both_numbers(self):
        """'Limit reached' alone leaves the owner with nothing to act on."""
        self.sub.emails_sent_this_month = 998
        self.sub.save(update_fields=['emails_sent_this_month'])

        error = str(self._send().data['error'])
        self.assertIn('5', error, 'should say how many the campaign needs')
        self.assertIn('2', error, 'should say how many remain')
        self.assertIn('1,000', error, 'should say what the plan allows')

    def test_a_campaign_within_quota_proceeds(self):
        response = self._send()

        self.assertEqual(response.status_code, 200)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'sending')


class QuotaExhaustionPausesTestCase(TestCase):
    """
    A mid-send block must pause, not spin.

    A blocked batch used to return silently, leaving recipients pending and the
    campaign 'sending' forever, so check_stuck_campaigns re-queued the whole
    fan-out every 30 minutes and every batch returned early again.
    """

    def setUp(self):
        create_plans()
        self.org = Organization.objects.create(name='Pause Co', slug='pause-co')
        self.sub = Subscription.objects.get(organization=self.org)
        self.user = User.objects.create_user(
            email='owner@pause.co', password='x', organization=self.org, role='owner',
        )
        self.campaign = Campaign.objects.create(
            organization=self.org, created_by=self.user, name='Mid',
            subject='Mid', status='sending', sent_at=timezone.now(),
        )

    def test_quota_exhaustion_pauses_the_campaign(self):
        from apps.campaigns.tasks import _quota_exhausted

        self.sub.emails_sent_this_month = 1000
        self.sub.save(update_fields=['emails_sent_this_month'])

        self.assertTrue(_quota_exhausted(self.campaign))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'paused')

    def test_a_paused_campaign_is_not_re_queued(self):
        """check_stuck_campaigns only picks up status='sending'."""
        from apps.campaigns.tasks import _quota_exhausted

        self.sub.emails_sent_this_month = 1000
        self.sub.save(update_fields=['emails_sent_this_month'])
        _quota_exhausted(self.campaign)

        contact = Contact.objects.create(organization=self.org, email='left@test.co')
        CampaignRecipient.objects.create(
            campaign=self.campaign, contact=contact, email=contact.email, status='pending',
        )
        self.campaign.sent_at = timezone.now() - timezone.timedelta(hours=2)
        self.campaign.save(update_fields=['sent_at'])

        from apps.campaigns.models import Campaign as C
        stuck = C.objects.filter(status='sending', sent_at__lt=timezone.now())
        self.assertNotIn(self.campaign, stuck)

    def test_within_quota_does_not_pause(self):
        from apps.campaigns.tasks import _quota_exhausted

        self.assertFalse(_quota_exhausted(self.campaign))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'sending')
