"""
The public snippet endpoint.

Unauthenticated and cross-site by nature, so it is a plain Django view rather
than a DRF one -- the same choice `apps/campaigns/tracking_views.py` makes for
the open pixel, and for the same reason: there is no user, no session and
nothing for authentication or permission classes to do.
"""
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from apps.accounts.models import Organization
from apps.forms.models import Form

from .snippet import CACHE_SECONDS, build_config, render

logger = logging.getLogger(__name__)

POPUP_TYPES = ('popup', 'slide_in', 'top_bar')


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

    forms = (
        Form.objects
        .filter(
            organization=organization,
            status='active',
            form_type__in=POPUP_TYPES,
        )
        .only('id', 'form_type', 'display_rules')
    )

    config = build_config(
        organization, forms,
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
