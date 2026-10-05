"""
Public tracking views for campaign open/click/unsubscribe events.
These views do NOT require authentication.
"""
import logging
from django.conf import settings
from django.core import signing
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# 1×1 transparent GIF (43 bytes)
TRANSPARENT_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
    b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00'
    b'\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
    b'\x44\x01\x00\x3b'
)


@method_decorator([never_cache, csrf_exempt], name='dispatch')
class TrackOpenView(View):
    """
    GET /track/o/<uuid:tracking_id>/
    Records an open event and returns a 1×1 transparent GIF.
    """

    def get(self, request, tracking_id):
        from .models import CampaignRecipient

        try:
            recipient = CampaignRecipient.objects.select_related('campaign').get(
                tracking_id=tracking_id
            )
            # Only record the first open
            if not recipient.opened_at:
                recipient.opened_at = timezone.now()
                recipient.status = 'opened'
                recipient.save(update_fields=['opened_at', 'status', 'updated_at'])
                logger.info(
                    f"Open tracked for recipient {recipient.id} "
                    f"in campaign {recipient.campaign_id}"
                )
        except CampaignRecipient.DoesNotExist:
            pass  # Silent fail — pixel still returns 200
        except Exception as exc:
            logger.error(f"Error tracking open for {tracking_id}: {exc}")

        return HttpResponse(TRANSPARENT_GIF, content_type='image/gif')


@method_decorator([never_cache, csrf_exempt], name='dispatch')
class TrackClickView(View):
    """
    GET /track/c/<uuid:link_id>/<uuid:tracking_id>/
    Records a click event and redirects to the original URL.
    """

    def get(self, request, link_id, tracking_id):
        from .models import CampaignLink, CampaignRecipient, CampaignLinkClick

        fallback_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')

        try:
            link = CampaignLink.objects.get(id=link_id)
            recipient = CampaignRecipient.objects.get(tracking_id=tracking_id)

            # Increment link click counter
            CampaignLink.objects.filter(id=link_id).update(
                click_count=link.click_count + 1
            )

            # Record click event
            CampaignLinkClick.objects.create(
                link=link,
                recipient=recipient,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )

            # Record first click on recipient
            if not recipient.clicked_at:
                recipient.clicked_at = timezone.now()
                recipient.status = 'clicked'
                recipient.save(update_fields=['clicked_at', 'status', 'updated_at'])

            logger.info(
                f"Click tracked: link {link_id}, recipient {recipient.id}"
            )
            return HttpResponseRedirect(link.original_url)

        except (CampaignLink.DoesNotExist, CampaignRecipient.DoesNotExist):
            pass
        except Exception as exc:
            logger.error(f"Error tracking click for link {link_id}: {exc}")

        return HttpResponseRedirect(fallback_url)


@method_decorator(csrf_exempt, name='dispatch')
class UnsubscribeView(View):
    """
    GET /unsubscribe/<str:token>/  — Confirmation page
    POST /unsubscribe/<str:token>/ — Process unsubscribe
    """

    MAX_AGE = 30 * 86400  # 30 days

    def _decode_token(self, token):
        """Return recipient_id string or None on error."""
        try:
            return signing.loads(token, salt='unsubscribe', max_age=self.MAX_AGE)
        except signing.SignatureExpired:
            return None
        except signing.BadSignature:
            return None

    def get(self, request, token):
        from .models import CampaignRecipient

        recipient_id = self._decode_token(token)
        if not recipient_id:
            return HttpResponse(self._expired_html(), content_type='text/html', status=400)

        try:
            recipient = CampaignRecipient.objects.select_related(
                'contact', 'campaign'
            ).get(id=recipient_id)
        except CampaignRecipient.DoesNotExist:
            return HttpResponse(self._expired_html(), content_type='text/html', status=400)

        html = self._confirm_html(
            campaign_name=recipient.campaign.name,
            email=recipient.email,
            token=token,
        )
        return HttpResponse(html, content_type='text/html')

    def post(self, request, token):
        from .models import CampaignRecipient

        recipient_id = self._decode_token(token)
        if not recipient_id:
            return HttpResponse(self._expired_html(), content_type='text/html', status=400)

        try:
            recipient = CampaignRecipient.objects.select_related('contact').get(
                id=recipient_id
            )
        except CampaignRecipient.DoesNotExist:
            return HttpResponse(self._expired_html(), content_type='text/html', status=400)

        # Unsubscribe the contact
        recipient.contact.unsubscribe()

        # Update recipient record
        recipient.status = 'unsubscribed'
        recipient.unsubscribed_at = timezone.now()
        recipient.save(update_fields=['status', 'unsubscribed_at', 'updated_at'])

        logger.info(f"Contact {recipient.contact.email} unsubscribed via campaign link")

        return HttpResponse(self._success_html(email=recipient.email), content_type='text/html')

    # --- HTML helpers ---

    def _confirm_html(self, campaign_name, email, token):
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unsubscribe</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f5f5; display: flex; align-items: center;
         justify-content: center; min-height: 100vh; margin: 0; }}
  .card {{ background: #fff; border-radius: 8px; padding: 40px; max-width: 480px;
           width: 90%; box-shadow: 0 2px 8px rgba(0,0,0,.12); text-align: center; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 8px; color: #111; }}
  p {{ color: #555; margin-bottom: 24px; line-height: 1.5; }}
  button {{ background: #e53e3e; color: #fff; border: none; padding: 12px 28px;
            border-radius: 6px; font-size: 1rem; cursor: pointer; }}
  button:hover {{ background: #c53030; }}
</style>
</head>
<body>
<div class="card">
  <h1>Unsubscribe</h1>
  <p>You are about to unsubscribe <strong>{email}</strong> from future emails
  related to <strong>{campaign_name}</strong> and similar campaigns.</p>
  <form method="post">
    <button type="submit">Confirm Unsubscribe</button>
  </form>
</div>
</body>
</html>"""

    def _success_html(self, email):
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unsubscribed</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f5f5; display: flex; align-items: center;
         justify-content: center; min-height: 100vh; margin: 0; }}
  .card {{ background: #fff; border-radius: 8px; padding: 40px; max-width: 480px;
           width: 90%; box-shadow: 0 2px 8px rgba(0,0,0,.12); text-align: center; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 8px; color: #111; }}
  p {{ color: #555; line-height: 1.5; }}
  .check {{ font-size: 3rem; margin-bottom: 16px; }}
</style>
</head>
<body>
<div class="card">
  <div class="check">&#10003;</div>
  <h1>You've been unsubscribed</h1>
  <p><strong>{email}</strong> has been removed from our mailing list.
  You will no longer receive marketing emails from us.</p>
</div>
</body>
</html>"""

    def _expired_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Invalid Link</title>
<style>
  body { font-family: sans-serif; text-align: center; padding: 60px; }
</style>
</head>
<body>
<h1>Invalid or expired link</h1>
<p>This unsubscribe link is no longer valid. Please contact support if needed.</p>
</body>
</html>"""


def _get_client_ip(request):
    """Extract the real client IP from request headers."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
