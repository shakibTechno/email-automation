"""
Suspension, at both levels.

`Organization.is_active` existed but was read in one place in the entire
codebase, so suspending a tenant previously did nothing: they could still log
in and still send. These assert the behaviour rather than the flag.
"""
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import ActivityLog, Organization, User
from apps.billing.testing import create_plans
from apps.core.permissions import IsOrganizationMember
from apps.email_config.services import EmailConfigService
from apps.landlord.services import SuspensionService


class SuspensionTestCase(TestCase):
    def setUp(self):
        create_plans()
        self.org = Organization.objects.create(name='Acme', slug='acme', email='a@acme.test')
        self.owner = User.objects.create_user(
            email='owner@acme.test', password='correct-horse-battery',
            organization=self.org, role='owner',
        )
        self.staff = User.objects.create_user(
            email='ops@platform.test', password='x', organization=None, is_staff=True,
        )
        # The mail server is not reachable from tests; suspension must still
        # update local state when the remote call cannot be made.
        patcher = patch('apps.email_config.provisioning.PostalProvisioningService.get_tenant',
                        return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _request(self, user):
        return type('R', (), {'user': user})()

    # ------------------------------------------------------------ sending
    def test_suspending_sending_blocks_sending_but_not_access(self):
        SuspensionService.suspend_sending(self.org, 'bought list', actor=self.staff)

        allowed, reason = EmailConfigService.check_sending_limits(self.org)
        self.assertFalse(allowed)
        self.assertIn('bought list', reason)

        self.assertTrue(
            IsOrganizationMember().has_permission(self._request(self.owner), None),
            'sending suspension must not take away access to their own data',
        )

    def test_resuming_sending_restores_it(self):
        SuspensionService.suspend_sending(self.org, 'bought list', actor=self.staff)
        SuspensionService.resume_sending(self.org, actor=self.staff)

        allowed, _ = EmailConfigService.check_sending_limits(self.org)
        self.assertTrue(allowed)

    # ------------------------------------------------------------ account
    def test_suspending_the_account_refuses_login(self):
        SuspensionService.suspend_account(self.org, 'non-payment', actor=self.staff)

        response = APIClient().post(
            '/api/v1/auth/login/',
            {'email': 'owner@acme.test', 'password': 'correct-horse-battery'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('suspended', str(response.data).lower())

    def test_suspending_the_account_refuses_an_already_issued_token(self):
        """
        An access token lives an hour. Checking only at login would leave a
        suspended tenant working normally until theirs expired.
        """
        client = APIClient()
        client.force_authenticate(user=self.owner)
        self.assertEqual(client.get('/api/v1/contacts/').status_code, 200)

        SuspensionService.suspend_account(self.org, 'non-payment', actor=self.staff)

        self.assertEqual(client.get('/api/v1/contacts/').status_code, 403)

    def test_account_suspension_implies_sending_suspension(self):
        SuspensionService.suspend_account(self.org, 'non-payment', actor=self.staff)

        allowed, _ = EmailConfigService.check_sending_limits(self.org)
        self.assertFalse(allowed)

    def test_restoring_the_account_restores_login_and_sending(self):
        SuspensionService.suspend_account(self.org, 'non-payment', actor=self.staff)
        SuspensionService.restore_account(self.org, actor=self.staff)
        self.org.refresh_from_db()

        self.assertTrue(self.org.is_active)
        self.assertIsNone(self.org.suspended_at)
        self.assertTrue(EmailConfigService.check_sending_limits(self.org)[0])

        response = APIClient().post(
            '/api/v1/auth/login/',
            {'email': 'owner@acme.test', 'password': 'correct-horse-battery'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

    def test_restoring_access_can_leave_sending_stopped(self):
        """A tenant suspended for deliverability may need its data back first."""
        SuspensionService.suspend_account(self.org, 'bounce rate', actor=self.staff)
        SuspensionService.restore_account(self.org, actor=self.staff, resume_sending=False)
        self.org.refresh_from_db()

        self.assertTrue(self.org.is_active)
        self.assertFalse(EmailConfigService.check_sending_limits(self.org)[0])

    # ------------------------------------------------------------ audit
    def test_every_action_is_logged_against_the_operator(self):
        SuspensionService.suspend_account(self.org, 'non-payment', actor=self.staff)

        entry = ActivityLog.objects.filter(
            organization=self.org, action='account_suspended'
        ).first()
        self.assertIsNotNone(entry, 'suspension must be attributable')
        self.assertEqual(entry.user, self.staff)
        self.assertEqual(entry.details.get('reason'), 'non-payment')


class SuspensionApiTestCase(TestCase):
    """The console endpoints that drive it."""

    def setUp(self):
        create_plans()
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.staff = User.objects.create_user(
            email='ops@platform.test', password='x', organization=None, is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.staff)
        patcher = patch('apps.email_config.provisioning.PostalProvisioningService.get_tenant',
                        return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_reason_is_required(self):
        """The tenant is shown this text, so an empty one is not acceptable."""
        for verb in ('suspend-sending', 'suspend-account'):
            with self.subTest(action=verb):
                response = self.api.post(
                    f'/api/v1/landlord/tenants/{self.org.id}/{verb}/', {}, format='json',
                )
                self.assertEqual(response.status_code, 400)
                self.org.refresh_from_db()
                self.assertTrue(self.org.is_active)

    def test_suspend_and_restore_round_trip(self):
        response = self.api.post(
            f'/api/v1/landlord/tenants/{self.org.id}/suspend-account/',
            {'reason': 'non-payment'}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_active'])
        self.assertEqual(response.data['suspension_reason'], 'non-payment')

        response = self.api.post(
            f'/api/v1/landlord/tenants/{self.org.id}/restore-account/', {}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_active'])
