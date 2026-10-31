"""
The public snippet endpoint.

Unauthenticated and cross-site by nature, so it is a plain Django view rather
than a DRF one -- the same choice `apps/campaigns/tracking_views.py` makes for
the open pixel, and for the same reason: there is no user, no session and
nothing for authentication or permission classes to do.
"""
import json
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import Organization
from apps.popups.models import Popup

from .services import (
    MAX_BODY_BYTES, MAX_EVENTS_PER_REQUEST, buffer_events,
)
from .snippet import CACHE_SECONDS, build_config, render
from .throttle import over_limit

logger = logging.getLogger(__name__)

@require_GET
@cache_control(public=True, max_age=CACHE_SECONDS)
def snippet(request):
    """
    `GET /t.js?k=<tracking_key>` -- the script, with this organization's
    popups inlined.

    Served as JavaScript whatever happens. A 404 page where a customer's site
    expects a script is a syntax error in their console and a support ticket;
    an empty script is a no-op they never notice.
    """
    key = request.GET.get('k', '').strip()
    organization = _organization_for(key)
    if organization is None:
        return _js('/* mailflow: unknown or missing site key */\n')

    # Published, inside its schedule, not deleted. Decided here rather than in
    # the browser so a visitor's clock cannot resurrect an expired popup.
    now = timezone.now()
    popups = (
        Popup.objects
        .filter(
            organization=organization,
            status=Popup.STATUS_PUBLISHED,
            deleted_at__isnull=True,
        )
        .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .select_related('form')
    )

    config = build_config(
        organization, popups,
        form_origin=getattr(settings, 'FRONTEND_URL', '') or '',
    )
    return _js(render(config))


def _organization_for(key):
    if not key:
        return None
    try:
        return Organization.objects.get(tracking_key=key, is_active=True)
    except (Organization.DoesNotExist, ValueError, ValidationError):
        # ValueError/ValidationError: the key is not a uuid at all. Same answer
        # as an unknown one -- the endpoint must not say which.
        return None



def _js(body):
    response = HttpResponse(body, content_type='application/javascript')
    # The script is per-organization, so a shared cache must key on the query
    # string. Django's cache_control sets max-age; this stops a proxy serving
    # one tenant's popups to another.
    response['Vary'] = 'Accept-Encoding'
    return response


@csrf_exempt
@require_POST
def collect(request):
    """
    `POST /track/collect` -- page views from the snippet.

    Sent with `navigator.sendBeacon` as text/plain, which is a *simple*
    request: no preflight, no CORS, and it survives the page unloading, which
    `fetch` does not reliably do. The browser still sends `Origin`, so it is
    still checkable.

    Always 204, whatever happened. A visitor's browser can do nothing with an
    error, and a 429 only tells an abuser their flood is working.
    """
    if int(request.META.get('CONTENT_LENGTH') or 0) > MAX_BODY_BYTES:
        return _no_content()

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return _no_content()

    key = str(payload.get('k') or '').strip()
    visitor_key = str(payload.get('vid') or '').strip()[:64]
    events = payload.get('e')
    if not (key and visitor_key and isinstance(events, list)):
        return _no_content()

    organization = _organization_for(key)
    if organization is None:
        return _no_content()

    # Keyed on the site, not the IP: an IP throttle punishes a whole office
    # behind one NAT and does nothing against a distributed flood.
    if over_limit(organization.id, request):
        return _no_content()

    buffer_events(organization.id, [
        {
            'vid': visitor_key,
            't': str(event.get('t') or 'pageview')[:30],
            'u': str(event.get('u') or '')[:2000],
            'p': str(event.get('p') or '')[:500],
            'ti': str(event.get('ti') or '')[:255],
            'r': str(event.get('r') or '')[:2000],
            'at': str(event.get('at') or '')[:40],
            # Only meaningful on popup events; ignored on a page view.
            'pu': str(event.get('pu') or '')[:36],
        }
        for event in events[:MAX_EVENTS_PER_REQUEST]
        if isinstance(event, dict)
    ])
    return _no_content()


def _no_content():
    response = HttpResponse(status=204)
    # sendBeacon ignores the body, but a proxy should not cache a write.
    response['Cache-Control'] = 'no-store'
    return response


@csrf_exempt
@require_POST
def audience(request):
    """
    `POST /track/audience` -- what this visitor matches, for targeting that
    the cached script cannot carry.

    Only called when an organization actually uses that targeting, and it
    answers in booleans about questions its own popups already ask. Handing a
    browser the list of segments someone belongs to would publish an
    organization's audience structure to anyone with dev tools open.
    """
    if int(request.META.get('CONTENT_LENGTH') or 0) > MAX_BODY_BYTES:
        return _json({})

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return _json({})

    organization = _organization_for(str(payload.get('k') or '').strip())
    visitor_key = str(payload.get('vid') or '').strip()[:64]
    if organization is None or not visitor_key:
        return _json({})
    if over_limit(organization.id, request):
        return _json({})

    from .audience import answer, country_for

    result = answer(organization, visitor_key)
    result['country'] = country_for(request)
    return _json(result)


def _json(payload):
    from django.http import JsonResponse

    response = JsonResponse(payload)
    # Per visitor, so nothing in between may cache it.
    response['Cache-Control'] = 'no-store'
    # Readable cross-origin, and `*` rather than an echoed Origin on purpose:
    # the body is booleans about questions the caller's own popups already
    # ask, it carries no credentials, and CORS_ALLOW_CREDENTIALS is globally
    # true -- an echoed origin would invite the browser to send cookies to an
    # endpoint that has no use for them.
    response['Access-Control-Allow-Origin'] = '*'
    return response
