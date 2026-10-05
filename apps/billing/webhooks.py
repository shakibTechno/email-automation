"""
Stripe webhook handler.
"""
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import StripeService, WebhookService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle incoming Stripe webhook events."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = StripeService.construct_webhook_event(payload, sig_header)
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return HttpResponse(status=400)

    try:
        WebhookService.handle_event(event)
    except Exception as e:
        logger.error(f"Webhook handler error for {event['type']}: {e}")
        return HttpResponse(status=500)

    return HttpResponse(status=200)
