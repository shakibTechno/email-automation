"""
Webhook ingestion: signature verification, dedupe, and event application.

Signatures are exercised against a real RSA key pair rather than a stub, since
this is the control that stops anyone forging a delivery event by POSTing to a
public endpoint.
"""
import base64
import json
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import Organization, User
from apps.campaigns.models import Campaign, CampaignRecipient
from apps.contacts.models import Contact
from apps.email_config.events import PostalEventService
from apps.email_config.models import SendingDomain
from apps.email_config.postal_client import normalize_event, reset_key_cache, verify_webhook
from apps.email_config.provisioning import PostalProvisioningService

from .stubs import FakeProvisioner, dns_records

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def sign(raw):
    """Sign raw bytes the way Postal does: RSA-SHA256, PKCS1v15, base64."""
    return base64.b64encode(
        _KEY.sign(raw, padding.PKCS1v15(), hashes.SHA256())
    ).decode('ascii')


def event_body(event='MessageSent', uuid='evt-1', postal_id=1000, token='tok1000',
               **payload_extra):
    payload = {
        'status': 'Sent',
        'message': {'id': postal_id, 'token': token,
                    'to': 'r0@example.com', 'tag': 'campaign-42'},
    }
    payload.update(payload_extra)
    return {'event': event, 'uuid': uuid, 'timestamp': 1761072000.12, 'payload': payload}


class SignatureVerificationTestCase(TestCase):
    def setUp(self):
        reset_key_cache()
        self.addCleanup(reset_key_cache)
        patcher = patch(
            'apps.email_config.postal_client._public_key',
            return_value=_KEY.public_key(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_genuine_signature_verifies(self):
        raw = json.dumps(event_body()).encode()
        self.assertTrue(verify_webhook(raw, sign(raw)))

    def test_a_tampered_body_fails(self):
        raw = json.dumps(event_body()).encode()
        signature = sign(raw)
        tampered = json.dumps(event_body(postal_id=9999)).encode()

        self.assertFalse(verify_webhook(tampered, signature))

    def test_a_missing_signature_fails(self):
        raw = json.dumps(event_body()).encode()
        self.assertFalse(verify_webhook(raw, ''))

    def test_a_garbage_signature_fails_rather_than_raising(self):
        raw = json.dumps(event_body()).encode()
        self.assertFalse(verify_webhook(raw, 'not-base64-at-all!!'))

    def test_verification_fails_closed_when_the_key_cannot_be_fetched(self):
        """An unverifiable event must never be treated as genuine."""
        import requests
        with patch(
            'apps.email_config.postal_client._public_key',
            side_effect=requests.RequestException('jwks unreachable'),
        ):
            raw = json.dumps(event_body()).encode()
            self.assertFalse(verify_webhook(raw, sign(raw)))


@override_settings(POSTAL_ENABLED=True, POSTAL_URL='https://mail.platform.test',
                   CELERY_TASK_ALWAYS_EAGER=True)
class WebhookEndpointTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        reset_key_cache()
        self.addCleanup(reset_key_cache)
        patcher = patch(
            'apps.email_config.postal_client._public_key',
            return_value=_KEY.public_key(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _post(self, body, signature=None, url='/webhooks/postal'):
        raw = json.dumps(body).encode()
        return self.client.post(
            url, data=raw, content_type='application/json',
            HTTP_X_POSTAL_SIGNATURE_256=signature if signature is not None else sign(raw),
        )

    def test_a_signed_event_is_accepted(self):
        with patch('apps.email_config.tasks.process_postal_event.delay') as queued:
            response = self._post(event_body())

        self.assertEqual(response.status_code, 200)
        queued.assert_called_once()

    def test_an_unsigned_event_is_rejected_and_not_queued(self):
        with patch('apps.email_config.tasks.process_postal_event.delay') as queued:
            response = self._post(event_body(), signature='')

        self.assertEqual(response.status_code, 401)
        queued.assert_not_called()

    def test_a_tampered_event_is_rejected(self):
        raw = json.dumps(event_body()).encode()
        signature = sign(raw)
        with patch('apps.email_config.tasks.process_postal_event.delay') as queued:
            response = self.client.post(
                '/webhooks/postal',
                data=json.dumps(event_body(postal_id=9999)).encode(),
                content_type='application/json',
                HTTP_X_POSTAL_SIGNATURE_256=signature,
            )
        self.assertEqual(response.status_code, 401)
        queued.assert_not_called()

    def test_a_replayed_event_is_a_no_op(self):
        """Postal retries on non-2xx, so the same uuid can arrive twice."""
        with patch('apps.email_config.tasks.process_postal_event.delay') as queued:
            first = self._post(event_body(uuid='evt-dupe'))
            second = self._post(event_body(uuid='evt-dupe'))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(queued.call_count, 1, 'the replay must not be processed again')

    def test_both_url_forms_work(self):
        """
        The provisioner writes the no-slash form into every tenant's webhook,
        and APPEND_SLASH would answer that POST with a 301 and lose the body.
        """
        for url in ('/webhooks/postal', '/webhooks/postal/'):
            with self.subTest(url=url):
                with patch('apps.email_config.tasks.process_postal_event.delay'):
                    response = self._post(event_body(uuid=f'evt-{url}'), url=url)
                self.assertEqual(response.status_code, 200)

    def test_an_unparseable_body_is_acked_not_retried(self):
        raw = b'{not json'
        response = self.client.post(
            '/webhooks/postal', data=raw, content_type='application/json',
            HTTP_X_POSTAL_SIGNATURE_256=sign(raw),
        )
        self.assertEqual(response.status_code, 200, 'malformed input will not improve on retry')

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get('/webhooks/postal').status_code, 405)


class EventMappingTestCase(TestCase):
    def test_tracking_events_are_ignored(self):
        """
        This platform does its own open and click tracking, so Postal's
        tracking stays off and these events should never be acted on.
        """
        for event in ('MessageLoaded', 'MessageLinkClicked'):
            with self.subTest(event=event):
                self.assertIsNone(normalize_event(event_body(event=event)))

    def test_unknown_events_are_ignored(self):
        self.assertIsNone(normalize_event(event_body(event='SomethingNew')))

    def test_delivery_events_map_to_internal_types(self):
        cases = {
            'MessageSent': 'delivered',
            'MessageDelayed': 'deferred',
            'MessageDeliveryFailed': 'bounced',
            'MessageBounced': 'bounced',
            'MessageHeld': 'held',
        }
        for event, expected in cases.items():
            with self.subTest(event=event):
                self.assertEqual(normalize_event(event_body(event=event))['type'], expected)

    def test_dns_error_is_recognised(self):
        body = {'event': 'DomainDNSError', 'uuid': 'e', 'timestamp': 1.0,
                'payload': {'domain': 'news.acme.com', 'error': 'SPF missing'}}
        normalized = normalize_event(body)

        self.assertEqual(normalized['type'], 'dns_error')
        self.assertEqual(normalized['domain'], 'news.acme.com')


@override_settings(POSTAL_ENABLED=True, POSTAL_URL='https://mail.platform.test')
class EventApplicationTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org, role='owner',
        )
        self.campaign = Campaign.objects.create(
            organization=self.org, created_by=self.user, name='c', subject='s',
            status='sending',
        )
        self.contact = Contact.objects.create(organization=self.org, email='r0@example.com')
        self.recipient = CampaignRecipient.objects.create(
            campaign=self.campaign, contact=self.contact, email='r0@example.com',
            status='sent', postal_id=1000, postal_token='tok1000',
        )
        self.suppress_patcher = patch('apps.email_config.tasks.sync_suppression.delay')
        self.suppress = self.suppress_patcher.start()
        self.addCleanup(self.suppress_patcher.stop)

    def test_delivered_sets_the_timestamp_and_status(self):
        PostalEventService.handle(event_body('MessageSent'))

        self.recipient.refresh_from_db()
        self.assertEqual(self.recipient.status, 'delivered')
        self.assertIsNotNone(self.recipient.delivered_at)

    def test_delivered_does_not_rewind_an_open(self):
        """
        The bug this guards: a delivery webhook routinely lands after the open
        pixel has fired, and a direct status assignment rewound 'opened' back
        to 'delivered', under-reporting engagement.
        """
        self.recipient.advance_status('opened', {'opened_at': self.recipient.created_at})

        PostalEventService.handle(event_body('MessageSent'))

        self.recipient.refresh_from_db()
        self.assertEqual(self.recipient.status, 'opened')
        self.assertIsNotNone(self.recipient.delivered_at, 'the timestamp is still recorded')

    def test_a_hard_bounce_stops_future_mail_to_the_contact(self):
        PostalEventService.handle(event_body(
            'MessageDeliveryFailed', status='HardFail',
            output='550 5.1.1 user unknown',
        ))

        self.recipient.refresh_from_db()
        self.contact.refresh_from_db()
        self.assertEqual(self.recipient.status, 'bounced')
        self.assertIsNotNone(self.recipient.bounced_at)
        self.assertIsNotNone(
            self.contact.bounced_at,
            'the recipient query filters on bounced_at, so this is what excludes them',
        )
        self.suppress.assert_called_once()

    def test_a_soft_failure_does_not_bounce_the_contact(self):
        """SoftFail is temporary; Postal will retry it."""
        PostalEventService.handle(event_body('MessageDeliveryFailed', status='SoftFail'))

        self.recipient.refresh_from_db()
        self.contact.refresh_from_db()
        self.assertEqual(self.recipient.status, 'sent')
        self.assertIsNone(self.contact.bounced_at)
        self.suppress.assert_not_called()

    def test_a_bounce_wins_over_an_open(self):
        """Terminal outcomes always apply: they change whether we may mail again."""
        self.recipient.advance_status('opened', {'opened_at': self.recipient.created_at})

        PostalEventService.handle(event_body('MessageDeliveryFailed', status='HardFail'))

        self.recipient.refresh_from_db()
        self.assertEqual(self.recipient.status, 'bounced')

    def test_matching_falls_back_to_the_token(self):
        self.recipient.postal_id = None
        self.recipient.save(update_fields=['postal_id'])

        PostalEventService.handle(event_body('MessageSent'))

        self.recipient.refresh_from_db()
        self.assertEqual(self.recipient.status, 'delivered')

    def test_an_unmatched_event_is_reported_not_raised(self):
        outcome = PostalEventService.handle(
            event_body('MessageSent', postal_id=55555, token='nope')
        )
        self.assertEqual(outcome, 'unmatched')

    def test_a_dns_error_rechecks_the_domain_and_disables_sending(self):
        provisioner = FakeProvisioner()
        with patch('apps.email_config.provisioning.get_provisioner', return_value=provisioner):
            PostalProvisioningService.add_domain(self.org, 'news.acme.com')
            domain = SendingDomain.objects.get(organization=self.org)
            PostalProvisioningService.check_domain(domain)
            domain.refresh_from_db()
            self.assertTrue(domain.sending_enabled)

            # DNS has since broken.
            provisioner.dns_result = dns_records(spf='Missing')
            PostalEventService.handle({
                'event': 'DomainDNSError', 'uuid': 'e', 'timestamp': 1.0,
                'payload': {'domain': 'news.acme.com', 'error': 'SPF record removed'},
            })

        domain.refresh_from_db()
        self.assertFalse(
            domain.sending_enabled,
            'a broken record must stop mail rather than let it go out unauthenticated',
        )
