"""
The team invitation email.

It was never implemented: `invite_member` wrote a log line saying an email
"would go here in production" and returned, so inviting a colleague created a
row and sent nothing. The invited person was never told, and the only copy of
their invitation token was in the application log.
"""
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Organization, TeamInvitation, User
from apps.accounts.services import TeamService


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_URL='https://app.example.com',
    APP_NAME='MailFlow',
)
class InvitationEmailTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.org = Organization.objects.create(name='Acme Co', slug='acme')
        self.owner = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner', first_name='Dana', last_name='Reed',
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    # -------------------------------------------------------------- it sends
    def test_inviting_a_member_sends_them_an_email(self):
        TeamService.invite_member(self.org, 'new@example.com', 'member', self.owner)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['new@example.com'])

    def test_the_subject_names_the_inviter_and_the_organization(self):
        """What the recipient sees before opening it is what decides whether they do."""
        TeamService.invite_member(self.org, 'new@example.com', 'member', self.owner)

        self.assertIn('Dana Reed', mail.outbox[0].subject)
        self.assertIn('Acme Co', mail.outbox[0].subject)

    def test_the_email_carries_a_working_accept_link(self):
        invitation = TeamService.invite_member(
            self.org, 'new@example.com', 'admin', self.owner,
        )

        body = mail.outbox[0].body + mail.outbox[0].alternatives[0][0]
        self.assertIn(
            f'https://app.example.com/accept-invitation?token={invitation.token}', body,
        )

    def test_it_sends_both_plain_text_and_html(self):
        TeamService.invite_member(self.org, 'new@example.com', 'member', self.owner)
        message = mail.outbox[0]

        self.assertTrue(message.body.strip(), 'the plain-text part is empty')
        self.assertEqual(message.alternatives[0][1], 'text/html')
        # The text part is derived from the HTML, so the link has to survive
        # the conversion or a plain-text reader cannot accept the invitation.
        self.assertIn('accept-invitation?token=', message.body)

    def test_replies_go_to_the_inviter_not_a_noreply_address(self):
        """The recipient's first question is whether it is real."""
        TeamService.invite_member(self.org, 'new@example.com', 'member', self.owner)

        self.assertEqual(mail.outbox[0].reply_to, ['owner@acme.test'])

    def test_the_role_is_named_in_the_body(self):
        TeamService.invite_member(self.org, 'new@example.com', 'admin', self.owner)

        self.assertIn('Admin', mail.outbox[0].alternatives[0][0])

    def test_resending_sends_again_with_the_new_token(self):
        invitation = TeamService.invite_member(
            self.org, 'new@example.com', 'member', self.owner,
        )
        old_token = invitation.token
        mail.outbox = []

        TeamService.resend_invitation(invitation, self.owner)

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].alternatives[0][0]
        self.assertIn(invitation.token, body)
        self.assertNotIn(old_token, body)

    # ------------------------------------------------- it records the outcome
    def test_a_successful_send_is_recorded(self):
        invitation = TeamService.invite_member(
            self.org, 'new@example.com', 'member', self.owner,
        )
        invitation.refresh_from_db()

        self.assertIsNotNone(invitation.email_sent_at)
        self.assertEqual(invitation.email_error, '')

    def test_a_failed_send_does_not_lose_the_invitation(self):
        """
        The invitation row is already valid and the link already works, so a
        mail failure must not undo it — the admin is told and given the link.
        """
        with patch('apps.core.mail.EmailMultiAlternatives.send') as send:
            send.side_effect = OSError('connection refused')
            invitation = TeamService.invite_member(
                self.org, 'new@example.com', 'member', self.owner,
            )

        invitation.refresh_from_db()
        self.assertEqual(TeamInvitation.objects.filter(pk=invitation.pk).count(), 1)
        self.assertIsNone(invitation.email_sent_at)
        self.assertIn('connection refused', invitation.email_error)

    def test_a_failed_send_is_reported_through_the_api(self):
        with patch('apps.core.mail.EmailMultiAlternatives.send') as send:
            send.side_effect = OSError('connection refused')
            response = self.api.post(
                '/api/v1/team/invite/',
                {'email': 'new@example.com', 'role': 'member'},
            )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['email_sent'])
        self.assertTrue(response.data['email_error'])
        # So the admin has something to do about it.
        self.assertIn('accept-invitation?token=', response.data['accept_url'])

    def test_a_successful_send_is_reported_through_the_api(self):
        response = self.api.post(
            '/api/v1/team/invite/',
            {'email': 'new@example.com', 'role': 'member'},
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['email_sent'])

    # ---------------------------------------------------------- the token leak
    def test_the_token_is_not_written_to_the_log(self):
        """
        It used to be, on every invite and every resend. Any application log was
        therefore a list of live invitations that anyone with log access could
        accept.
        """
        with self.assertLogs('apps.accounts.services', level='INFO') as logs:
            invitation = TeamService.invite_member(
                self.org, 'new@example.com', 'member', self.owner,
            )

        self.assertNotIn(invitation.token, '\n'.join(logs.output))

    def test_the_token_is_not_logged_on_resend_either(self):
        invitation = TeamService.invite_member(
            self.org, 'new@example.com', 'member', self.owner,
        )

        with self.assertLogs('apps.accounts.services', level='INFO') as logs:
            TeamService.resend_invitation(invitation, self.owner)

        self.assertNotIn(invitation.token, '\n'.join(logs.output))

    def test_the_accept_url_is_withheld_once_the_invitation_is_spent(self):
        invitation = TeamService.invite_member(
            self.org, 'new@example.com', 'member', self.owner,
        )
        TeamService.cancel_invitation(invitation, self.owner)
        invitation.refresh_from_db()

        from apps.accounts.serializers import TeamInvitationSerializer

        self.assertIsNone(TeamInvitationSerializer(invitation).data['accept_url'])
