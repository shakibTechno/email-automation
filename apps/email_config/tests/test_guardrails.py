"""
Deliverability guardrails.

All tenants share one sending IP, so one organization mailing a bad list can
get that IP blocked for everyone. These tests cover the thresholds that were
already configurable but that nothing enforced.
"""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.campaigns.models import Campaign, CampaignRecipient
from apps.contacts.models import Contact
from apps.email_config.guardrails import MIN_VOLUME, evaluate, measure
from apps.email_config.models import EmailConfiguration, SendingDomain
from apps.email_config.provisioning import PostalProvisioningService

from .stubs import FakeProvisioner


@override_settings(POSTAL_ENABLED=True, POSTAL_URL='https://mail.platform.test')
class GuardrailTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org, role='owner',
        )
        self.config = EmailConfiguration.objects.create(
            organization=self.org, provider='platform_default',
            bounce_threshold_pct=5, complaint_threshold_pct=0.10,
        )
        self.campaign = Campaign.objects.create(
            organization=self.org, created_by=self.user, name='c', subject='s',
            status='sent',
        )
        self.provisioner = FakeProvisioner()
        patcher = patch(
            'apps.email_config.provisioning.get_provisioner',
            return_value=self.provisioner,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        PostalProvisioningService.add_domain(self.org, 'news.acme.com')
        PostalProvisioningService.check_domain(
            SendingDomain.objects.get(organization=self.org)
        )
        self.tenant = PostalProvisioningService.get_tenant(self.org)

    def _seed(self, sent, bounced=0, complained=0, age_days=1):
        """Create `sent` sent recipients, of which some bounced or complained."""
        when = timezone.now() - timedelta(days=age_days)
        for index in range(sent):
            contact = Contact.objects.create(
                organization=self.org, email=f'seed{index}-{age_days}@example.com',
            )
            CampaignRecipient.objects.create(
                campaign=self.campaign, contact=contact, email=contact.email,
                status='sent', sent_at=when,
                bounced_at=when if index < bounced else None,
                complained_at=when if bounced <= index < bounced + complained else None,
            )

    # -------------------------------------------------------------- measuring
    def test_measure_reports_rates_as_a_percentage_of_sends(self):
        self._seed(sent=100, bounced=7, complained=1)

        metrics = measure(self.org)

        self.assertEqual(metrics['sent'], 100)
        self.assertEqual(metrics['bounced'], 7)
        self.assertEqual(metrics['bounce_rate'], 7.0)
        self.assertEqual(metrics['complaint_rate'], 1.0)

    def test_measure_ignores_sends_outside_the_window(self):
        self._seed(sent=100, bounced=50, age_days=30)

        self.assertEqual(measure(self.org)['sent'], 0)

    def test_measure_on_an_org_that_has_never_sent(self):
        metrics = measure(self.org)
        self.assertEqual(metrics['sent'], 0)
        self.assertEqual(metrics['bounce_rate'], 0.0)

    # ------------------------------------------------------------- evaluating
    def test_low_volume_is_not_judged(self):
        """
        Two bounces out of three sends is 67% and means nothing. Without a
        floor, every new customer's first test send would suspend them.
        """
        self._seed(sent=3, bounced=2)

        result = evaluate(self.org)

        self.config.refresh_from_db()
        self.assertEqual(result['action'], 'skipped_low_volume')
        self.assertFalse(self.config.sending_paused_due_to_threshold)

    def test_clean_sending_is_left_alone(self):
        self._seed(sent=MIN_VOLUME * 2, bounced=1)

        result = evaluate(self.org)

        self.config.refresh_from_db()
        self.assertEqual(result['action'], 'none')
        self.assertFalse(self.config.sending_paused_due_to_threshold)
        self.assertNotIn('suspend', self.provisioner.call_names())

    def test_a_bounce_breach_pauses_locally_and_suspends_the_tenant(self):
        self._seed(sent=100, bounced=10)   # 10% against a 5% limit

        result = evaluate(self.org)

        self.config.refresh_from_db()
        self.tenant.refresh_from_db()
        self.assertEqual(result['action'], 'paused_and_suspended')
        self.assertTrue(
            self.config.sending_paused_due_to_threshold,
            'check_sending_limits() reads this flag to stop our own queue',
        )
        self.assertTrue(
            self.tenant.is_suspended,
            'without suspending the tenant, mail would keep leaving the server',
        )
        self.assertIn('bounce rate', self.tenant.suspension_reason)

    def test_a_complaint_breach_also_pauses(self):
        self._seed(sent=1000, complained=5)   # 0.5% against a 0.10% limit

        result = evaluate(self.org)

        self.config.refresh_from_db()
        self.assertTrue(self.config.sending_paused_due_to_threshold)
        self.assertIn('complaint rate', result['reason'])

    def test_a_breach_at_exactly_the_threshold_does_not_pause(self):
        self._seed(sent=100, bounced=5)   # exactly 5%, the limit

        evaluate(self.org)

        self.config.refresh_from_db()
        self.assertFalse(self.config.sending_paused_due_to_threshold)

    def test_the_local_pause_holds_when_the_provisioner_is_unreachable(self):
        from apps.email_config.provisioner_client import ProvisionerError
        self._seed(sent=100, bounced=10)
        self.provisioner.fail_with = ProvisionerError(0, 'unreachable', 'down')

        result = evaluate(self.org)

        self.config.refresh_from_db()
        self.assertEqual(result['action'], 'paused_suspend_failed')
        self.assertTrue(
            self.config.sending_paused_due_to_threshold,
            'our own queue must stop even if the remote call failed',
        )

    def test_evaluating_twice_does_not_re_suspend(self):
        self._seed(sent=100, bounced=10)
        evaluate(self.org)
        self.provisioner.calls.clear()

        evaluate(self.org)

        self.assertNotIn('suspend', self.provisioner.call_names())

    def test_admins_are_notified_when_sending_stops(self):
        from apps.notifications.models import Notification
        self._seed(sent=100, bounced=10)

        evaluate(self.org)

        notification = Notification.objects.filter(
            organization=self.org, notification_type='sending_paused',
        ).first()
        self.assertIsNotNone(notification, 'a silent pause looks like an outage')


@override_settings(POSTAL_ENABLED=True, POSTAL_URL='https://mail.platform.test')
class ResumeTestCase(TestCase):
    """Resuming must lift the suspension in Postal too, not just the local flag."""

    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org, role='owner',
        )
        self.config = EmailConfiguration.objects.create(
            organization=self.org, provider='platform_default',
            sending_paused_due_to_threshold=True,
        )
        self.provisioner = FakeProvisioner()
        patcher = patch(
            'apps.email_config.provisioning.get_provisioner',
            return_value=self.provisioner,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.tenant = PostalProvisioningService.get_or_create_tenant(self.org)
        PostalProvisioningService.suspend(self.tenant, 'bounce rate 10%')

        # The API authenticates with JWT, so a session login does not apply.
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_resume_clears_the_flag_and_unsuspends_the_tenant(self):
        response = self.api.post('/api/v1/email-config/resume/')

        self.assertEqual(response.status_code, 200)
        self.config.refresh_from_db()
        self.tenant.refresh_from_db()
        self.assertFalse(self.config.sending_paused_due_to_threshold)
        self.assertFalse(
            self.tenant.is_suspended,
            'mail would stay held at the server if only the local flag cleared',
        )

    def test_a_member_cannot_resume(self):
        """Resuming after a breach affects the shared IP, so it is admin-only."""
        member = User.objects.create_user(
            email='member@acme.test', password='x', organization=self.org, role='member',
        )
        self.api.force_authenticate(user=member)

        response = self.api.post('/api/v1/email-config/resume/')

        self.assertEqual(response.status_code, 403)
        self.config.refresh_from_db()
        self.assertTrue(self.config.sending_paused_due_to_threshold)
