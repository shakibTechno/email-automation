"""
Postal webhook receiver.

Mirrors the shape of apps/billing/webhooks.py: a CSRF-exempt POST-only view
that verifies the signature against the raw request body, then hands off.

Two constraints drive the design:

  * Postal waits at most 5 seconds and retries on any non-2xx response, so this
    view does no database work beyond a dedupe check — the event is queued and
    acknowledged immediately.
  * The signature covers the raw bytes. Re-serialising parsed JSON changes them
    and verification fails, so request.body is passed through untouched.
"""
import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .postal_client import verify_webhook

logger = logging.getLogger(__name__)

# Postal retries a failed delivery 5 times over about 36 minutes, so a dedupe
# window comfortably longer than that makes a replay a no-op.
_DEDUPE_TTL = 2 * 60 * 60


@csrf_exempt
@require_POST
def postal_webhook(request):
    """Handle an inbound Postal delivery event."""
    raw = request.body

    if settings.POSTAL_WEBHOOK_VERIFY:
        signature = request.META.get('HTTP_X_POSTAL_SIGNATURE_256', '')
        if not verify_webhook(raw, signature):
            logger.warning('Rejected a Postal webhook with an invalid signature')
            return HttpResponse('invalid signature', status=401)

    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        # Malformed and will not improve on retry; ack so Postal stops.
        logger.warning('Discarded a Postal webhook with an unparseable body')
        return HttpResponse(status=200)

    if not isinstance(body, dict):
        return HttpResponse(status=200)

    event_uuid = body.get('uuid')
    if event_uuid:
        # cache.add is atomic, so a concurrent retry cannot slip past.
        if not cache.add(f'postal:event:{event_uuid}', 1, _DEDUPE_TTL):
            logger.debug('Ignored duplicate Postal event %s', event_uuid)
            return HttpResponse(status=200)

    # `tenant` is appended by the provisioner but sits outside the signature,
    # so it is a routing hint only — events are matched on postal_id/token.
    tenant_hint = request.GET.get('tenant', '')

    from .tasks import process_postal_event
    process_postal_event.delay(body, tenant_hint)

    return HttpResponse(status=200)
