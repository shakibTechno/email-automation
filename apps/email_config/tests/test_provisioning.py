"""
Tenant provisioning and domain verification.

The headline test here is test_domain_is_not_verified_until_every_record_passes:
the code this replaced marked a domain verified without performing a single DNS
lookup, which let anyone claim a domain they did not own.
"""
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.accounts.models import Organization
from apps.email_config.models import PostalTenant, SendingDomain
from apps.email_config.provisioner_client import ProvisionerError
from apps.email_config.provisioning import (
    PostalProvisioningService,
    build_external_id,
    resolve_send_limit,
)

from .stubs import FakeProvisioner, dns_records


@override_settings(POSTAL_ENABLED=True, POSTAL_URL='https://mail.platform.test')
class ProvisioningTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.provisioner = FakeProvisioner()
        self._patcher = patch(
            'apps.email_config.provisioning.get_provisioner',
            return_value=self.provisioner,
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    # ---------------------------------------------------------- external ids
    def test_external_id_satisfies_the_provisioner_contract(self):
        """1-48 chars of a-z, 0-9 and '-', starting with an alphanumeric."""
        import re
        pattern = re.compile(r'\A[a-z0-9][a-z0-9-]{0,47}\Z')

        cases = [
            Organization(name='Acme', slug='acme-inc'),
            # Underscores are legal in a Django slug but not in an external id.
            Organization(name='Acme Corp', slug='acme_corp'),
            # Far longer than the 48-character budget.
            Organization(name='Long', slug='a' * 200),
            # slugify() of a non-Latin name returns '' — this used to be the
            # case that produced an invalid id.
            Organization(name='株式会社', slug=''),
        ]
        for org in cases:
            org.id = Organization._meta.get_field('id').get_default()
            external_id = build_external_id(org)
            self.assertRegex(external_id, pattern, f'bad id for slug {org.slug!r}')
            self.assertLessEqual(len(external_id), 48)

    def test_external_id_is_stable_across_renames(self):
        tenant = PostalProvisioningService.get_or_create_tenant(self.org)
        original = tenant.external_id

        self.org.name = 'Renamed Co'
        self.org.slug = 'renamed-co'
        self.org.save()

        again = PostalProvisioningService.get_or_create_tenant(self.org)
        self.assertEqual(again.external_id, original)

    # -------------------------------------------------------------- tenants
    def test_creates_a_tenant_and_stores_the_api_key(self):
        tenant = PostalProvisioningService.get_or_create_tenant(self.org)

        self.assertEqual(tenant.organization, self.org)
        self.assertTrue(tenant.postal_tenant_id)
        self.assertTrue(tenant.api_key, 'the key is only returned once and must be stored')
        self.assertEqual(tenant.status, PostalTenant.STATUS_ACTIVE)
        self.assertIn('create_tenant', self.provisioner.call_names())

    def test_get_or_create_is_idempotent(self):
        first = PostalProvisioningService.get_or_create_tenant(self.org)
        self.provisioner.calls.clear()

        second = PostalProvisioningService.get_or_create_tenant(self.org)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PostalTenant.objects.count(), 1)
        self.assertEqual(
            self.provisioner.calls, [],
            'a complete tenant should not be re-provisioned',
        )

    def test_adopts_a_tenant_created_by_an_earlier_failed_attempt(self):
        """
        A previous run created the mail server but crashed before storing the
        key. The key is unrecoverable, so it has to be rotated rather than
        leaving the organization permanently unable to send.
        """
        external_id = build_external_id(self.org)
        self.provisioner.create_tenant(external_id, 'Acme Inc')
        self.provisioner.calls.clear()

        tenant = PostalProvisioningService.get_or_create_tenant(self.org)

        self.assertTrue(tenant.api_key)
        self.assertIn('rotate_api_key', self.provisioner.call_names())
        self.assertNotIn('create_tenant', self.provisioner.call_names())

    def test_sync_refreshes_the_cached_metrics(self):
        tenant = PostalProvisioningService.get_or_create_tenant(self.org)
        PostalProvisioningService.sync_tenant(tenant)

        tenant.refresh_from_db()
        self.assertEqual(tenant.queued, 3)
        self.assertEqual(tenant.held, 1)
        self.assertEqual(float(tenant.bounce_rate_30d), 1.25)
        self.assertIsNotNone(tenant.last_synced_at)

    def test_suspend_and_unsuspend_round_trip(self):
        tenant = PostalProvisioningService.get_or_create_tenant(self.org)

        PostalProvisioningService.suspend(tenant, 'complaint rate 0.6%')
        tenant.refresh_from_db()
        self.assertTrue(tenant.is_suspended)
        self.assertEqual(tenant.suspension_reason, 'complaint rate 0.6%')

        PostalProvisioningService.unsuspend(tenant)
        tenant.refresh_from_db()
        self.assertEqual(tenant.status, PostalTenant.STATUS_ACTIVE)
        self.assertEqual(tenant.suspension_reason, '')

    # --------------------------------------------------------------- domains
    def test_adding_a_domain_provisions_the_tenant_lazily(self):
        self.assertFalse(PostalTenant.objects.exists())

        domain = PostalProvisioningService.add_domain(self.org, 'news.acme.com')

        self.assertTrue(PostalTenant.objects.filter(organization=self.org).exists())
        self.assertEqual(domain.domain, 'news.acme.com')
        self.assertFalse(domain.sending_enabled)
        self.assertEqual(domain.status, SendingDomain.STATUS_PENDING)

    def test_adding_a_domain_mirrors_all_four_dns_records(self):
        domain = PostalProvisioningService.add_domain(self.org, 'news.acme.com')

        purposes = [record['purpose'] for record in domain.dns_records]
        self.assertEqual(purposes, ['spf', 'dkim', 'return_path', 'dmarc'])
        # The DKIM value must be a real key from Postal, not a placeholder. The
        # code this replaced stored a hardcoded 'p=MIGfMA0GCSqGSIb3...' string.
        dkim = next(r for r in domain.dns_records if r['purpose'] == 'dkim')
        self.assertIn('v=DKIM1', dkim['value'])
        self.assertNotIn('generate via openssl', dkim['value'])

    def test_domain_is_not_verified_until_every_record_passes(self):
        """
        Each record in turn is the one that blocks sending.

        This is the regression guard for the old verify_domain(), which read
        `if spf_found or not txt_records:` and so marked a domain verified when
        DNS returned nothing at all.
        """
        PostalProvisioningService.add_domain(self.org, 'news.acme.com')
        domain = SendingDomain.objects.get(organization=self.org)

        for failing in ('spf', 'dkim', 'return_path', 'dmarc'):
            with self.subTest(missing=failing):
                self.provisioner.dns_result = dns_records(**{failing: 'Missing'})
                ok, message = PostalProvisioningService.check_domain(domain)

                domain.refresh_from_db()
                self.assertFalse(ok, f'{failing} missing must block sending')
                self.assertFalse(domain.sending_enabled)
                self.assertIn(failing, message)

    def test_domain_verifies_once_all_records_pass(self):
        PostalProvisioningService.add_domain(self.org, 'news.acme.com')
        domain = SendingDomain.objects.get(organization=self.org)

        self.provisioner.dns_result = dns_records()
        ok, _ = PostalProvisioningService.check_domain(domain)

        domain.refresh_from_db()
        self.assertTrue(ok)
        self.assertTrue(domain.sending_enabled)
        self.assertEqual(domain.status, SendingDomain.STATUS_VERIFIED)
        self.assertIsNotNone(domain.verified_at)

    def test_a_broken_record_turns_sending_back_off(self):
        """Verification is not permanent: if DNS breaks later, sending stops."""
        PostalProvisioningService.add_domain(self.org, 'news.acme.com')
        domain = SendingDomain.objects.get(organization=self.org)
        PostalProvisioningService.check_domain(domain)
        domain.refresh_from_db()
        self.assertTrue(domain.sending_enabled)

        self.provisioner.dns_result = dns_records(dkim='Missing')
        PostalProvisioningService.check_domain(domain)

        domain.refresh_from_db()
        self.assertFalse(domain.sending_enabled)
        self.assertEqual(domain.status, SendingDomain.STATUS_FAILED)

    def test_check_records_the_error_when_the_provisioner_is_unreachable(self):
        PostalProvisioningService.add_domain(self.org, 'news.acme.com')
        domain = SendingDomain.objects.get(organization=self.org)
        self.provisioner.fail_with = ProvisionerError(0, 'unreachable', 'connection refused')

        ok, message = PostalProvisioningService.check_domain(domain)

        domain.refresh_from_db()
        self.assertFalse(ok)
        self.assertFalse(domain.sending_enabled)
        self.assertIn('connection refused', domain.last_check_error)
        self.assertIn('connection refused', message)

    def test_can_send_requires_a_sending_enabled_domain(self):
        tenant = PostalProvisioningService.get_or_create_tenant(self.org)
        self.assertFalse(
            tenant.can_send,
            'a tenant with no verified domain cannot send: Postal would reject '
            'the From address',
        )

        PostalProvisioningService.add_domain(self.org, 'news.acme.com')
        domain = SendingDomain.objects.get(organization=self.org)
        PostalProvisioningService.check_domain(domain)

        self.assertTrue(tenant.can_send)

    # ----------------------------------------------------------- send limits
    def test_send_limit_falls_back_when_an_org_has_no_subscription(self):
        """
        New organizations have no Subscription row, because
        BillingService.initialize_subscription() is never called. The limit
        resolver has to cope rather than raise.
        """
        limit = resolve_send_limit(self.org)
        self.assertGreater(limit, 0)
