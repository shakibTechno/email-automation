"""
The Postal send backend and how get_connection() resolves to it.

The rule being protected here is Postal's: one API call per recipient. Putting
several people in one call would show them each other's addresses and give them
a shared unsubscribe link.
"""
from unittest.mock import patch

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.test import TestCase, override_settings

from apps.accounts.models import Organization, User
from apps.campaigns.models import Campaign, CampaignRecipient
from apps.contacts.models import Contact
from apps.email_config.backends import PostalEmailBackend
from apps.email_config.models import EmailConfiguration, SendingDomain
from apps.email_config.postal_client import PostalError, html_to_text
from apps.email_config.provisioning import PostalProvisioningService
from apps.email_config.services import EmailConfigService

from .stubs import FakePostal, FakeProvisioner


@override_settings(POSTAL_ENABLED=True, POSTAL_URL='https://mail.platform.test')
class PostalBackendTestCase(TestCase):
    def setUp(self):
        self.postal = FakePostal()
        patcher = patch('apps.email_config.backends.send_message', self.postal)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.backend = PostalEmailBackend(api_key='key-1')

    def test_one_api_call_per_recipient(self):
        """Three addresses on one message must become three separate sends."""
        msg = EmailMessage(
            subject='October deals', body='<p>Hi</p>',
            from_email='Acme <deals@news.acme.com>',
            to=['a@example.com', 'b@example.com', 'c@example.com'],
            connection=self.backend,
        )
        msg.content_subtype = 'html'
        msg.send()

        self.assertEqual(len(self.postal.sent), 3)
        self.assertEqual(
            [s['to'] for s in self.postal.sent],
            ['a@example.com', 'b@example.com', 'c@example.com'],
        )
        for send in self.postal.sent:
            self.assertIsInstance(send['to'], str, 'to must be a single address')

    def test_cc_and_bcc_are_expanded_not_passed_through(self):
        msg = EmailMessage(
            subject='s', body='b', from_email='a@news.acme.com',
            to=['to@example.com'], cc=['cc@example.com'], bcc=['bcc@example.com'],
            connection=self.backend,
        )
        msg.send()

        addresses = [s['to'] for s in self.postal.sent]
        self.assertEqual(addresses, ['to@example.com', 'cc@example.com', 'bcc@example.com'])

    def test_html_only_message_gets_a_derived_text_part(self):
        """Campaign mail is HTML-only, but Postal wants both parts."""
        msg = EmailMessage(
            subject='s', body='<p>Hello <b>there</b></p><p>Second</p>',
            from_email='a@news.acme.com', to=['to@example.com'],
            connection=self.backend,
        )
        msg.content_subtype = 'html'
        msg.send()

        sent = self.postal.sent[0]
        self.assertIn('<p>', sent['html'])
        self.assertNotIn('<p>', sent['text'])
        self.assertIn('Hello there', sent['text'])

    def test_multialternatives_message_is_read_correctly(self):
        """Sequences build EmailMultiAlternatives with an empty body."""
        msg = EmailMultiAlternatives(
            subject='s', body='', from_email='a@news.acme.com',
            to=['to@example.com'], connection=self.backend,
        )
        msg.attach_alternative('<h1>Step one</h1>', 'text/html')
        msg.send()

        sent = self.postal.sent[0]
        self.assertEqual(sent['html'], '<h1>Step one</h1>')
        self.assertIn('Step one', sent['text'])

    def test_unsubscribe_headers_and_tag_are_passed_through(self):
        msg = EmailMessage(
            subject='s', body='<p>x</p>', from_email='a@news.acme.com',
            to=['to@example.com'],
            headers={
                'List-Unsubscribe': '<https://app.test/u/abc>',
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                'X-Campaign-ID': 'campaign-42',
            },
            connection=self.backend,
        )
        msg.content_subtype = 'html'
        msg.send()

        sent = self.postal.sent[0]
        self.assertEqual(sent['headers']['List-Unsubscribe'], '<https://app.test/u/abc>')
        self.assertEqual(
            sent['headers']['List-Unsubscribe-Post'], 'List-Unsubscribe=One-Click'
        )
        self.assertEqual(sent['tag'], 'campaign-42', 'tag comes back on every webhook')

    def test_postal_ids_are_exposed_on_the_message(self):
        msg = EmailMessage(
            subject='s', body='<p>x</p>', from_email='a@news.acme.com',
            to=['to@example.com'], connection=self.backend,
        )
        msg.send()

        self.assertIsNotNone(msg.postal_status)
        self.assertEqual(msg.postal_status['postal_id'], 1000)
        self.assertEqual(msg.postal_status['token'], 'tok1000')

    def test_a_permanent_error_propagates(self):
        """
        UnauthenticatedFromAddress means the sending domain is not verified.
        It must surface rather than be retried forever.
        """
        self.postal.error = PostalError('UnauthenticatedFromAddress', 'not verified')
        msg = EmailMessage(
            subject='s', body='x', from_email='a@unverified.test',
            to=['to@example.com'], connection=self.backend,
        )
        with self.assertRaises(PostalError) as caught:
            msg.send()
        self.assertTrue(caught.exception.is_permanent)

    def test_fail_silently_swallows_errors(self):
        self.postal.error = PostalError('unreachable', 'connection refused')
        backend = PostalEmailBackend(api_key='key-1', fail_silently=True)
        msg = EmailMessage(
            subject='s', body='x', from_email='a@news.acme.com',
            to=['to@example.com'], connection=backend,
        )
        self.assertEqual(msg.send(), 0)


class HtmlToTextTestCase(TestCase):
    def test_strips_markup_and_keeps_readable_text(self):
        html = (
            '<html><head><style>p{color:red}</style></head><body>'
            '<h1>Welcome</h1><p>Hello &amp; goodbye</p>'
            '<script>alert(1)</script><p>Line two</p></body></html>'
        )
        text = html_to_text(html)

        self.assertIn('Welcome', text)
        self.assertIn('Hello & goodbye', text)
        self.assertIn('Line two', text)
        self.assertNotIn('color:red', text, 'style content must not leak into the text part')
        self.assertNotIn('alert(1)', text, 'script content must not leak into the text part')
        self.assertNotIn('<', text)

    def test_empty_input_is_safe(self):
        self.assertEqual(html_to_text(''), '')
        self.assertEqual(html_to_text(None), '')


@override_settings(POSTAL_ENABLED=True, POSTAL_URL='https://mail.platform.test')
class ConnectionResolutionTestCase(TestCase):
    """How EmailConfigService.get_connection() chooses a backend."""

    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.provisioner = FakeProvisioner()
        patcher = patch(
            'apps.email_config.provisioning.get_provisioner',
            return_value=self.provisioner,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _verified_tenant(self):
        PostalProvisioningService.add_domain(self.org, 'news.acme.com')
        domain = SendingDomain.objects.get(organization=self.org)
        PostalProvisioningService.check_domain(domain)

    def test_platform_default_uses_postal_once_a_domain_is_verified(self):
        EmailConfiguration.objects.create(organization=self.org, provider='platform_default')
        self._verified_tenant()

        connection = EmailConfigService.get_connection(self.org)
        self.assertIsInstance(connection, PostalEmailBackend)

    def test_platform_default_falls_back_without_a_verified_domain(self):
        """
        A free or trial organization has no tenant yet. It must keep working on
        the platform's shared SMTP rather than fail.
        """
        EmailConfiguration.objects.create(organization=self.org, provider='platform_default')

        connection = EmailConfigService.get_connection(self.org)
        self.assertNotIsInstance(connection, PostalEmailBackend)

    def test_postal_provider_falls_back_when_not_yet_usable(self):
        """
        Explicitly set to Postal but with no verified domain: transactional mail
        should still go out rather than hard-fail on
        UnauthenticatedFromAddress.
        """
        EmailConfiguration.objects.create(organization=self.org, provider='postal')

        connection = EmailConfigService.get_connection(self.org)
        self.assertNotIsInstance(connection, PostalEmailBackend)

    def test_own_provider_is_never_overridden_by_postal(self):
        """A customer who brought their own ESP keeps using it."""
        EmailConfiguration.objects.create(
            organization=self.org, provider='smtp', smtp_host='smtp.theirhost.com',
        )
        self._verified_tenant()

        connection = EmailConfigService.get_connection(self.org)
        self.assertNotIsInstance(connection, PostalEmailBackend)
        self.assertEqual(connection.host, 'smtp.theirhost.com')

    @override_settings(POSTAL_ENABLED=False)
    def test_master_switch_off_disables_postal_entirely(self):
        EmailConfiguration.objects.create(organization=self.org, provider='platform_default')
        self._verified_tenant()

        connection = EmailConfigService.get_connection(self.org)
        self.assertNotIsInstance(connection, PostalEmailBackend)


@override_settings(POSTAL_ENABLED=True, POSTAL_URL='https://mail.platform.test')
class CampaignSendTestCase(TestCase):
    """The campaign task must persist the ids a webhook will arrive with."""

    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org, role='owner',
        )
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

        EmailConfiguration.objects.create(
            organization=self.org, provider='platform_default',
            from_name='Acme', from_email='deals@news.acme.com',
        )
        PostalProvisioningService.add_domain(self.org, 'news.acme.com')
        PostalProvisioningService.check_domain(
            SendingDomain.objects.get(organization=self.org)
        )

        self.campaign = Campaign.objects.create(
            organization=self.org, created_by=self.user, name='October deals',
            subject='October deals', status='sending',
        )

    def _recipient(self, email):
        contact = Contact.objects.create(organization=self.org, email=email)
        return CampaignRecipient.objects.create(
            campaign=self.campaign, contact=contact, email=email, status='pending',
        )

    def test_send_records_postal_ids_on_each_recipient(self):
        from apps.campaigns.tasks import send_campaign_email_batch

        recipients = [self._recipient(f'r{i}@example.com') for i in range(3)]
        send_campaign_email_batch(
            str(self.campaign.id), [str(r.id) for r in recipients]
        )

        self.assertEqual(len(self.postal.sent), 3, 'one API call per recipient')
        for recipient in recipients:
            recipient.refresh_from_db()
            self.assertEqual(recipient.status, 'sent')
            self.assertIsNotNone(recipient.postal_id)
            self.assertTrue(recipient.postal_token)

        ids = {r.postal_id for r in CampaignRecipient.objects.all()}
        self.assertEqual(len(ids), 3, 'each recipient needs its own provider id')

    def test_each_recipient_gets_its_own_unsubscribe_link(self):
        recipients = [self._recipient(f'r{i}@example.com') for i in range(3)]
        from apps.campaigns.tasks import send_campaign_email_batch
        send_campaign_email_batch(
            str(self.campaign.id), [str(r.id) for r in recipients]
        )

        links = {s['headers'].get('List-Unsubscribe') for s in self.postal.sent}
        self.assertEqual(
            len(links), 3,
            'a shared unsubscribe link would let one recipient unsubscribe another',
        )
