"""
Postal send API client and webhook verifier.

Ported from mailstack/examples/python/postal.py, which is written against
Postal's real API and webhook format. See mailstack/INTEGRATION.md.

Two separate concerns live here:

  * sending      — one HTTP call per recipient, with the tenant's own API key
  * verification — the RSA-SHA256 signature on inbound webhooks

Both are deliberately free of Django model imports so they can be unit-tested
against stubs.
"""
import base64
import logging
import re
import time

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.conf import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 30
_JWKS_TTL = 3600

# Postal errors that will never succeed on retry: the message itself is wrong.
# Retrying them burns queue capacity and, for UnauthenticatedFromAddress, hides
# a misconfigured sending domain behind what looks like a transient failure.
PERMANENT_ERROR_CODES = frozenset({
    'UnauthenticatedFromAddress',
    'NoRecipients',
    'NoContent',
    'FromAddressMissing',
    'TooManyToAddresses',
    'AttachmentMissingName',
    'AttachmentMissingData',
    'ValidationError',
})


class PostalError(Exception):
    """A non-success response from Postal's send API."""

    def __init__(self, code, message=''):
        super().__init__(f'{code}: {message}'.rstrip(': '))
        self.code = str(code)
        self.message = message

    @property
    def is_permanent(self):
        """True when retrying cannot help. Callers must not re-queue these."""
        return self.code in PERMANENT_ERROR_CODES


# ──────────────────────────────────────────────────────────────── plain text
_STYLE_RE = re.compile(r'<(script|style)\b[^>]*>.*?</\1>', re.IGNORECASE | re.DOTALL)
_BREAK_RE = re.compile(r'<(br|/p|/div|/tr|/h[1-6])\b[^>]*>', re.IGNORECASE)
_TAG_RE = re.compile(r'<[^>]+>')
_WS_RE = re.compile(r'[ \t]+')
_BLANK_RE = re.compile(r'\n{3,}')

_ENTITIES = [
    ('&nbsp;', ' '), ('&amp;', '&'), ('&lt;', '<'),
    ('&gt;', '>'), ('&quot;', '"'), ('&#39;', "'"),
]


def html_to_text(html):
    """
    Derive a plain-text part from HTML.

    Postal wants both html_body and plain_body (INTEGRATION.md §2) and campaign
    mail in this platform is HTML-only, so this is a fallback rather than a
    substitute for authoring real text. It drops script/style content, turns
    block-level closings into newlines, and strips the rest.
    """
    if not html:
        return ''
    text = _STYLE_RE.sub('', html)
    text = _BREAK_RE.sub('\n', text)
    text = _TAG_RE.sub('', text)
    for entity, char in _ENTITIES:
        text = text.replace(entity, char)
    text = _WS_RE.sub(' ', text)
    text = '\n'.join(line.strip() for line in text.splitlines())
    return _BLANK_RE.sub('\n\n', text).strip()


# ──────────────────────────────────────────────────────────────────── sending
def send_message(*, api_key, to, from_, subject, html, text=None, reply_to=None,
                 tag=None, headers=None, attachments=None, base_url=None,
                 timeout=_TIMEOUT):
    """
    Send one message to one recipient.

    Returns {'message_id': str, 'postal_id': int, 'token': str}. Store postal_id
    and token on the send record: every webhook carries them, and they are the
    only reliable way to match an event back to a recipient.

    `to` must be a single address. Postal accepts a list, but putting several
    people in one call would show them each other's addresses and give them a
    shared unsubscribe link (INTEGRATION.md §2).
    """
    url = (base_url or settings.POSTAL_URL or '').rstrip('/')
    if not url:
        raise PostalError('not_configured', 'POSTAL_URL is not set')
    if not api_key:
        raise PostalError('not_configured', 'No Postal API key for this organization')

    payload = {
        'to': [to],
        'from': from_,
        'subject': subject,
        'plain_body': text if text is not None else html_to_text(html),
        'tag': tag,
        'headers': headers or {},
    }
    # Omit rather than send an empty html_body: a text-only message (the config
    # test send, for one) has no HTML part and Postal should not be handed one.
    if html:
        payload['html_body'] = html
    if reply_to:
        payload['reply_to'] = reply_to
    if attachments:
        payload['attachments'] = attachments

    try:
        response = requests.post(
            f'{url}/api/v1/send/message',
            json=payload,
            headers={'X-Server-API-Key': api_key},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        # Transient: the caller may retry.
        raise PostalError('unreachable', str(exc)) from exc

    try:
        body = response.json()
    except ValueError:
        raise PostalError(response.status_code, 'Postal returned a non-JSON response')

    if response.status_code != 200 or body.get('status') != 'success':
        data = body.get('data') or {}
        raise PostalError(data.get('code', response.status_code), data.get('message', ''))

    data = body['data']
    messages = data.get('messages') or {}
    # Postal keys the result by recipient; fall back to the only entry if the
    # address was normalised (e.g. case-folded) on the way through.
    receipt = messages.get(to) or (next(iter(messages.values())) if messages else {})
    return {
        'message_id': data.get('message_id'),
        'postal_id': receipt.get('id'),
        'token': receipt.get('token'),
    }


# ─────────────────────────────────────────────────────── webhook verification
_key_cache = {'key': None, 'at': 0.0, 'url': None}


def _b64url_int(value):
    return int.from_bytes(base64.urlsafe_b64decode(value + '=' * (-len(value) % 4)), 'big')


def _public_key(base_url):
    """Fetch and cache Postal's webhook public key from its JWKS endpoint."""
    url = (base_url or settings.POSTAL_URL or '').rstrip('/')
    fresh = (
        _key_cache['key'] is not None
        and _key_cache['url'] == url
        and time.time() - _key_cache['at'] < _JWKS_TTL
    )
    if fresh:
        return _key_cache['key']

    jwks = requests.get(f'{url}/.well-known/jwks.json', timeout=10).json()
    jwk = jwks['keys'][0]
    key = rsa.RSAPublicNumbers(_b64url_int(jwk['e']), _b64url_int(jwk['n'])).public_key()
    _key_cache.update(key=key, at=time.time(), url=url)
    return key


def reset_key_cache():
    """Drop the cached JWKS key. Used by tests and after a Postal key rotation."""
    _key_cache.update(key=None, at=0.0, url=None)


def verify_webhook(raw_body, signature_header, base_url=None):
    """
    Verify a Postal webhook signature.

    `raw_body` must be the exact request bytes. Re-serialising the parsed JSON
    changes the bytes and the signature will not match.
    """
    if not signature_header:
        return False
    try:
        _public_key(base_url).verify(
            base64.b64decode(signature_header),
            raw_body,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except (InvalidSignature, ValueError, KeyError, IndexError):
        return False
    except requests.RequestException as exc:
        # Could not reach the JWKS endpoint. Fail closed: an unverified event
        # must never be treated as genuine.
        logger.error('Could not fetch Postal JWKS to verify a webhook: %s', exc)
        return False


# ───────────────────────────────────────────────────────────── event mapping
# Postal event -> our internal event type. Mapping per INTEGRATION.md §4.
# MessageLoaded and MessageLinkClicked are deliberately absent: this platform
# does its own open and click tracking (pixel + wrapped links), so Postal's
# tracking stays off and those events are never emitted.
EVENT_TYPES = {
    'MessageSent': 'delivered',
    'MessageDelayed': 'deferred',
    'MessageDeliveryFailed': 'bounced',
    'MessageBounced': 'bounced',
    'MessageHeld': 'held',
}


def normalize_event(body):
    """
    Flatten a Postal webhook body into a dict our handler can act on.

    Returns None for events we do not act on, so the caller can ack and move on.
    """
    payload = body.get('payload') or {}
    event = body.get('event')

    if event == 'DomainDNSError':
        return {
            'type': 'dns_error',
            'uuid': body.get('uuid'),
            'domain': payload.get('domain'),
            'at': body.get('timestamp'),
            'details': payload.get('error') or payload.get('details'),
        }

    event_type = EVENT_TYPES.get(event)
    if not event_type:
        return None

    message = payload.get('message') or payload.get('original_message') or {}
    return {
        'type': event_type,
        'uuid': body.get('uuid'),
        'postal_id': message.get('id'),
        'token': message.get('token'),
        'email': message.get('to'),
        'tag': message.get('tag'),
        'at': body.get('timestamp'),
        'status': payload.get('status'),
        'details': payload.get('details'),
        'output': payload.get('output'),
    }
