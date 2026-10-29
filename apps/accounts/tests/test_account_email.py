"""
The two emails that prove someone owns an address.

Both are sent on the day an organization signs up, before it has verified any
sending domain of its own, which is why they are platform mail.
"""
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.models import (
    EmailVerificationToken, Organization, PasswordResetToken, User,
)
from apps.accounts.services import AccountEmailService


class PasswordResetEmailTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='ada@acme.test', password='correct horse', organization=self.org,
            role='owner', first_name='Ada',
        )

    def _request(self, email='ada@acme.test'):
        return self.client.post(
            reverse('accounts:password-reset'), {'email': email}, format='json'
        )

    def test_a_reset_request_actually_sends_the_link(self):
        """It used to only log the token, so the link never reached anyone."""
        response = self._request()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertIn(token.token, mail.outbox[0].body)

    def test_the_link_points_at_the_page_that_collects_the_password(self):
        self._request()
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertIn(f'/reset-password?token={token.token}', mail.outbox[0].body)

    def test_an_unknown_address_is_answered_the_same_way_and_sends_nothing(self):
        """The response must not say whether an address has an account."""
        known = self._request()
        mail.outbox.clear()
        unknown = self._request('nobody@example.test')

        self.assertEqual(unknown.status_code, known.status_code)
        self.assertEqual(unknown.json(), known.json())
        self.assertEqual(mail.outbox, [])

    def test_the_token_is_not_written_to_the_log(self):
        with self.assertLogs('apps.accounts.views', level='INFO') as logs:
            self._request()
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertNotIn(token.token, chr(10).join(logs.output))

    def test_the_emailed_link_completes_the_reset(self):
        self._request()
        token = PasswordResetToken.objects.get(user=self.user)

        response = self.client.post(
            reverse('accounts:password-reset-confirm'),
            {
                'token': token.token,
                'new_password': 'a new strong passphrase',
                'new_password_confirm': 'a new strong passphrase',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('a new strong passphrase'))


class RegistrationVerificationTests(APITestCase):
    PAYLOAD = {
        'email': 'new@acme.test',
        'password': 'a strong passphrase here',
        'password_confirm': 'a strong passphrase here',
        'first_name': 'Grace',
        'last_name': 'Hopper',
        'organization_name': 'Hopper Ltd',
    }

    def test_signing_up_without_an_invitation_sends_a_confirmation(self):
        response = self.client.post(
            reverse('accounts:register'), self.PAYLOAD, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(len(mail.outbox), 1)
        user = User.objects.get(email='new@acme.test')
        token = EmailVerificationToken.objects.get(user=user)
        self.assertIn(f'/verify-email?token={token.token}', mail.outbox[0].body)

    def test_the_account_works_before_the_address_is_confirmed(self):
        """
        A failed or unread confirmation must not lock someone out of an account
        they just created.
        """
        response = self.client.post(
            reverse('accounts:register'), self.PAYLOAD, format='json'
        )

        self.assertIn('tokens', response.data)
        user = User.objects.get(email='new@acme.test')
        self.assertFalse(user.is_email_verified)
        self.assertTrue(user.is_active)


class EmailVerificationTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='ada@acme.test', password='x', organization=self.org, role='owner',
        )

    def _token(self):
        AccountEmailService.send_verification(self.user)
        return EmailVerificationToken.objects.filter(
            user=self.user, is_used=False
        ).latest('created_at')

    def _verify(self, raw):
        return self.client.post(
            reverse('accounts:verify-email'), {'token': raw}, format='json'
        )

    def test_a_valid_token_confirms_the_address(self):
        response = self._verify(self._token().token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_a_token_cannot_be_spent_twice(self):
        token = self._token().token
        self._verify(token)

        self.assertEqual(self._verify(token).status_code, status.HTTP_400_BAD_REQUEST)

    def test_an_unknown_token_is_refused_the_same_way_as_a_spent_one(self):
        """
        Separating them tells an anonymous caller whether an address has an
        account here.
        """
        spent = self._token().token
        self._verify(spent)

        self.assertEqual(
            self._verify('not-a-real-token').json(), self._verify(spent).json()
        )

    def test_resending_invalidates_the_previous_link(self):
        """Otherwise several live links sit in an inbox at once."""
        first = self._token().token
        self._token()

        self.assertEqual(self._verify(first).status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_requires_signing_in(self):
        response = self.client.post(reverse('accounts:verify-email-resend'))
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_resend_sends_to_the_signed_in_user_only(self):
        self.client.force_authenticate(user=self.user)
        mail.outbox.clear()

        response = self.client.post(reverse('accounts:verify-email-resend'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([m.to for m in mail.outbox], [['ada@acme.test']])

    def test_an_already_confirmed_address_is_not_emailed_again(self):
        self.user.is_email_verified = True
        self.user.save(update_fields=['is_email_verified'])
        self.client.force_authenticate(user=self.user)
        mail.outbox.clear()

        response = self.client.post(reverse('accounts:verify-email-resend'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mail.outbox, [])


class ResetThrottleTests(APITestCase):
    """
    Password reset is unauthenticated and emails whatever address it is given,
    which makes it an amplifier for bombing an inbox from our sending domain.
    """

    def setUp(self):
        Organization.objects.create(name='Acme Inc', slug='acme-inc')
        # Throttle state is cache state, and it outlives a test.
        cache.clear()
        self.addCleanup(cache.clear)

    def test_repeated_requests_are_refused(self):
        # DRF binds THROTTLE_RATES as a class attribute at import, so
        # override_settings cannot reach it -- the rate has to be patched where
        # the throttle actually reads it.
        patcher = patch.dict(
            SimpleRateThrottle.THROTTLE_RATES,
            {'password_reset': '2/hour'},
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        url = reverse('accounts:password-reset')
        codes = [
            self.client.post(url, {'email': 'nobody@example.test'},
                             format='json').status_code
            for _ in range(4)
        ]

        self.assertEqual(codes[:2], [status.HTTP_200_OK, status.HTTP_200_OK])
        self.assertEqual(
            codes[2:],
            [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_429_TOO_MANY_REQUESTS],
        )
