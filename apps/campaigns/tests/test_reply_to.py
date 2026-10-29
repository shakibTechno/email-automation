"""
Where a campaign's reply-to address comes from.

A user's personal reply-to is a *default*, stamped onto the campaign when they
create it. It is deliberately never consulted at send time: a scheduled
campaign is sent by a worker with no current user, and an organization's
newsletter must not redirect replies to whoever happened to press Send.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, User
from apps.campaigns.models import Campaign


class CampaignReplyToTestCase(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.rep = User.objects.create_user(
            email='rep@acme.test', password='x', organization=self.org,
            role='admin', reply_to_email='rep.personal@acme.test',
        )
        self.no_default = User.objects.create_user(
            email='marketing@acme.test', password='x', organization=self.org,
            role='admin',
        )

    def _create(self, user, name='October', **extra):
        self.client.force_authenticate(user=user)
        payload = {'name': name, 'subject': 'Hello'}
        payload.update(extra)
        response = self.client.post(reverse('campaigns:campaign-list'), payload, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.data
        )
        # The create serializer does not echo the id back.
        return Campaign.objects.get(organization=self.org, name=name)

    def test_creator_personal_reply_to_is_applied(self):
        campaign = self._create(self.rep)
        self.assertEqual(campaign.reply_to_email, 'rep.personal@acme.test')

    def test_an_explicit_reply_to_wins_over_the_personal_default(self):
        campaign = self._create(self.rep, reply_to_email='support@acme.test')
        self.assertEqual(campaign.reply_to_email, 'support@acme.test')

    def test_a_user_without_one_leaves_the_campaign_blank(self):
        """Blank means the organization's address applies, as it did before."""
        campaign = self._create(self.no_default)
        self.assertEqual(campaign.reply_to_email, '')

    def test_the_stamp_happens_once_and_the_campaign_owns_it(self):
        """
        Changing a personal default must not retroactively change campaigns
        already created -- the campaign is the record of what was decided.
        """
        campaign = self._create(self.rep)
        self.rep.reply_to_email = 'moved@acme.test'
        self.rep.save(update_fields=['reply_to_email'])

        campaign.refresh_from_db()
        self.assertEqual(campaign.reply_to_email, 'rep.personal@acme.test')
