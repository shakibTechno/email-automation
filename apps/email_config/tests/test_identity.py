"""
How a sending identity is resolved, and what happens when there is none.

The rule being protected here is Postal's: it accepts a From address only on a
domain it has verified for that tenant. So the backend and the From address
cannot be chosen independently — every case below is really one question, "will
the backend we picked accept the address we picked?", and the old code answered
it in two places that could disagree.
"""
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.accounts.models import Organization
from apps.email_config.models import EmailConfiguration, SendingDomain
from apps.email_config.provisioning import PostalProvisioningService
from apps.email_config.services import EmailConfigService

from .stubs import FakePostal, FakeProvisioner

SHARED = dict(
    POSTAL_ENABLED=True,
    POSTAL_URL='https://mail.platform.test',
    POSTAL_SHARED_API_KEY='shared-key',
    POSTAL_SHARED_FROM_EMAIL='hello@platform.test',
)


@override_settings(**SHARED)
class ResolveIdentityTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.postal = FakePostal()
        patcher = patch('apps.email_config.backends.send_message', self.postal)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.provisioner = FakeProvisioner()
        prov_patcher = patch(
            'apps.email_config.provisioning.get_provisioner',
            return_value=self.provisioner,
        )
        prov_patcher.start()
        self.addCleanup(prov_patcher.stop)

    def _verify(self, name='news.acme.com'):
        PostalProvisioningService.add_domain(self.org, name)
        domain = SendingDomain.objects.get(organization=self.org, domain=name)
        PostalProvisioningService.check_domain(domain)
        return domain

    def _config(self, **kwargs):
        kwargs.setdefault('provider', 'platform_default')
        return EmailConfiguration.objects.create(organization=self.org, **kwargs)

    # ------------------------------------------------------------ own domain
    def test_own_domain_is_used_when_the_from_address_sits_on_it(self):
        self._verify()
        self._config(from_name='Acme', from_email='deals@news.acme.com')

        identity = EmailConfigService.resolve(self.org)

        self.assertFalse(identity.is_shared)
        self.assertEqual(identity.from_email, 'deals@news.acme.com')
        self.assertEqual(identity.unavailable, '')

    def test_verified_domain_with_no_from_address_sends_from_that_domain(self):
        """
        Verifying a domain and never filling in the From field is the normal
        state right after onboarding. It must not read as "cannot send".
        """
        self._verify()
        self._config(from_name='Acme')

        identity = EmailConfigService.resolve(self.org)

        self.assertFalse(identity.is_shared)
        self.assertEqual(identity.from_email, 'noreply@news.acme.com')

    def test_from_address_on_a_removed_domain_falls_back_to_shared(self):
        """
        The case that broke in production: a sending domain was deleted and the
        From address was left behind pointing at it. Postal would reject that
        outright, so the shared identity carries the message instead.
        """
        self._verify()
        self._config(from_name='Acme', from_email='hello@gone.acme.com')

        identity = EmailConfigService.resolve(self.org)

        self.assertTrue(identity.is_shared)
        self.assertEqual(identity.from_email, 'hello@platform.test')
        # The address they meant to send as is not lost — replies go there.
        self.assertEqual(identity.reply_to, 'hello@gone.acme.com')

    # --------------------------------------------------------- shared sender
    def test_organization_with_no_domain_uses_the_shared_identity(self):
        self._config(from_name='Acme', from_email='hello@acme.com')

        identity = EmailConfigService.resolve(self.org)

        self.assertTrue(identity.is_shared)
        self.assertEqual(identity.from_email, 'hello@platform.test')
        self.assertEqual(identity.connection.api_key, 'shared-key')

    def test_shared_identity_keeps_the_display_name(self):
        """The address is the platform's; the name the recipient reads is not."""
        self._config(from_name='Acme', from_email='hello@acme.com')

        header, reply_to = EmailConfigService.resolve(self.org).sender()

        self.assertEqual(header, 'Acme <hello@platform.test>')
        self.assertEqual(reply_to, ['hello@acme.com'])

    def test_shared_identity_refuses_a_per_message_sender_override(self):
        """
        A campaign may name its own sender. On the shared identity that address
        is unverified, so it becomes the reply address rather than the From.
        """
        self._config(from_name='Acme', from_email='hello@acme.com')

        header, reply_to = EmailConfigService.resolve(self.org).sender(
            name='Acme Sales', email='sales@acme.com'
        )

        self.assertEqual(header, 'Acme Sales <hello@platform.test>')
        self.assertEqual(reply_to, ['sales@acme.com'])

    def test_own_identity_honours_a_per_message_sender_override(self):
        self._verify()
        self._config(from_name='Acme', from_email='deals@news.acme.com')

        header, _ = EmailConfigService.resolve(self.org).sender(
            name='Acme Sales', email='sales@news.acme.com'
        )

        self.assertEqual(header, 'Acme Sales <sales@news.acme.com>')

    # ------------------------------------------------------- nothing to send
    @override_settings(POSTAL_SHARED_API_KEY='', POSTAL_SHARED_FROM_EMAIL='',
                   EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
                   EMAIL_HOST='localhost')
    def test_no_domain_and_no_shared_sender_is_reported_not_attempted(self):
        self._config(from_name='Acme', from_email='hello@acme.com')

        identity = EmailConfigService.resolve(self.org)

        self.assertIsNone(identity.connection)
        self.assertIn('verify a sending domain', identity.unavailable)

    @override_settings(POSTAL_SHARED_API_KEY='', POSTAL_SHARED_FROM_EMAIL='',
                   EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
                   EMAIL_HOST='localhost')
    def test_test_connection_reports_the_reason_without_opening_a_socket(self):
        """
        This used to surface as "[Errno 111] Connection refused" from Django's
        unconfigured default SMTP backend, which named neither the real problem
        nor anything the reader could act on.
        """
        self._config(from_name='Acme', from_email='hello@acme.com')

        ok, message = EmailConfigService.test_connection(self.org, 'qa@example.com')

        self.assertFalse(ok)
        self.assertIn('verify a sending domain', message)
        self.assertNotIn('Errno', message)
        self.assertEqual(self.postal.sent, [])

    def test_test_connection_says_when_it_used_the_shared_address(self):
        self._config(from_name='Acme', from_email='hello@acme.com')

        ok, message = EmailConfigService.test_connection(self.org, 'qa@example.com')

        self.assertTrue(ok)
        self.assertIn('hello@platform.test', message)
        self.assertEqual(len(self.postal.sent), 1)

    @override_settings(POSTAL_SHARED_API_KEY='', POSTAL_SHARED_FROM_EMAIL='',
                   EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
                   EMAIL_HOST='localhost')
    def test_smtp_without_a_host_is_reported_not_attempted(self):
        self._config(provider='smtp', from_email='hello@acme.com')

        identity = EmailConfigService.resolve(self.org)

        self.assertIsNone(identity.connection)
        self.assertIn('no server address', identity.unavailable)

    @override_settings(POSTAL_SHARED_API_KEY='', POSTAL_SHARED_FROM_EMAIL='')
    def test_a_configured_default_backend_is_still_a_valid_platform_default(self):
        """
        A deployment that runs its own mail server had working transactional
        mail before the shared identity existed, and must keep it. Only the
        untouched localhost:25 default counts as "nothing to send through".
        """
        self._config(from_name='Acme', from_email='hello@acme.com')

        identity = EmailConfigService.resolve(self.org)

        self.assertEqual(identity.unavailable, '')
        self.assertIsNotNone(identity.connection)
        self.assertFalse(identity.is_shared)
