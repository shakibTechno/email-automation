"""
Where a test email's backend and From address come from.

This is the first thing anyone tries on the platform, and it used to be the
only send path that ignored the organization's email configuration: a bare
send_mail() reached for Django's default backend -- localhost:25, nothing
inside a container -- so it failed with "Connection refused" while every real
campaign sent fine.
"""
from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, User
from apps.campaigns.models import Campaign
from apps.campaigns.services import CampaignService
from apps.email_config.services import SendingIdentity


class TestEmailSendingTestCase(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.campaign = Campaign.objects.create(
            organization=self.org, name='October', subject='Hello',
            sender_name='Acme', sender_email='news@acme.test',
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.user)

    def _identity(self, **kwargs):
        defaults = dict(
            connection=mail.get_connection(
                'django.core.mail.backends.locmem.EmailBackend'),
            from_name='Acme', from_email='news@acme.test', reply_to='',
            is_shared=False,
        )
        defaults.update(kwargs)
        return SendingIdentity(**defaults)

    def test_it_sends_through_the_resolved_connection(self):
        identity = self._identity()
        with patch('apps.email_config.services.EmailConfigService.resolve',
                   return_value=identity):
            sent = CampaignService.send_test_email(self.campaign, ['me@acme.test'])

        self.assertEqual(sent, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['me@acme.test'])
        self.assertTrue(mail.outbox[0].subject.startswith('[TEST]'))

    def test_the_html_body_travels_as_an_alternative(self):
        with patch('apps.email_config.services.EmailConfigService.resolve',
                   return_value=self._identity()):
            with patch.object(CampaignService, 'render_html',
                              return_value='<p>Hi</p>'):
                CampaignService.send_test_email(self.campaign, ['me@acme.test'])

        self.assertEqual(
            mail.outbox[0].alternatives, [('<p>Hi</p>', 'text/html')]
        )

    def test_the_campaign_sender_is_honoured_on_its_own_identity(self):
        with patch('apps.email_config.services.EmailConfigService.resolve',
                   return_value=self._identity()):
            CampaignService.send_test_email(self.campaign, ['me@acme.test'])

        self.assertEqual(mail.outbox[0].from_email, 'Acme <news@acme.test>')

    def test_a_shared_identity_sends_as_the_platform_and_replies_to_the_org(self):
        """
        Postal only accepts a From whose domain it verified for that tenant,
        so the requested address becomes the reply address rather than being
        silently dropped.
        """
        identity = self._identity(
            from_email='hello@send.mailflow.ie', is_shared=True,
        )
        with patch('apps.email_config.services.EmailConfigService.resolve',
                   return_value=identity):
            CampaignService.send_test_email(self.campaign, ['me@acme.test'])

        self.assertEqual(mail.outbox[0].from_email, 'Acme <hello@send.mailflow.ie>')
        self.assertEqual(mail.outbox[0].reply_to, ['news@acme.test'])

    def test_no_identity_refuses_with_the_sentence_not_a_socket_error(self):
        identity = self._identity(
            connection=None,
            unavailable='Add and verify a sending domain first.',
        )
        with patch('apps.email_config.services.EmailConfigService.resolve',
                   return_value=identity):
            with self.assertRaises(RuntimeError) as caught:
                CampaignService.send_test_email(self.campaign, ['me@acme.test'])

        self.assertIn('verify a sending domain', str(caught.exception))
        self.assertEqual(len(mail.outbox), 0)

    def test_the_endpoint_reports_the_reason_rather_than_claiming_success(self):
        identity = self._identity(
            connection=None, unavailable='Add and verify a sending domain first.',
        )
        url = reverse('campaigns:campaign-send-test', args=[self.campaign.id])
        with patch('apps.email_config.services.EmailConfigService.resolve',
                   return_value=identity):
            response = self.client.post(
                url, {'test_emails': ['me@acme.test']}, format='json',
            )

        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('verify a sending domain', str(response.data))
