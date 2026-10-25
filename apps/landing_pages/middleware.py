"""
Deciding which tenant — if any — a request's hostname belongs to.
"""
import logging

from django.http import HttpResponseBadRequest
from django.utils import timezone

from .domains import is_platform_host, normalize_domain, resolve_domain

logger = logging.getLogger(__name__)

# Only touch last_seen_at this often per host. It exists to tell "DNS is wrong"
# apart from "DNS is right but nobody has visited", which one write per burst
# of traffic answers just as well as one write per request.
_SEEN_THROTTLE_SECONDS = 300


class LandingHostMiddleware:
    """
    Resolves the request's Host header to the platform or to a connected
    landing domain, and refuses anything else.

    **This middleware replaces Django's ALLOWED_HOSTS check and must run
    first.** Customer domains cannot be enumerated in settings, so production
    sets ALLOWED_HOSTS to ['*'] and the real gate moves here. That is only a
    fair trade because this check is stricter than the one it replaces: it also
    decides *which URLs each host may serve*.

    A connected domain gets `request.urlconf` swapped to the landing-only
    URLconf. That is the mechanism that keeps the API, the admin and the SPA off
    a customer's hostname — on that host those routes do not exist at all,
    rather than existing and being refused. Absent beats forbidden here: there
    is no view to reach, so no view can be careless.

    Fails closed. An unrecognised host is answered with a bare 400 before any
    other middleware or view runs.
    """

    LANDING_URLCONF = 'config.urls_landing'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Read the header directly rather than via get_host(): with
        # ALLOWED_HOSTS=['*'] get_host() would not raise, but it also applies
        # X_FORWARDED_HOST handling we have not yet decided to trust for an
        # unknown host.
        raw_host = request.META.get('HTTP_HOST') or request.META.get('SERVER_NAME') or ''
        host = normalize_domain(raw_host) or raw_host.strip().lower().split(':')[0]

        if not host or is_platform_host(host):
            request.landing_domain = None
            request.landing_organization_id = None
            return self.get_response(request)

        row = resolve_domain(host)
        if row is None:
            # No detail in the body: a scanner learns nothing about which hosts
            # exist, and a misconfigured customer domain is diagnosed from the
            # settings page rather than from this response.
            logger.info("Rejected request for unrecognised host %r", host[:200])
            return HttpResponseBadRequest('Unknown host.')

        request.landing_domain = row
        request.landing_organization_id = row['organization_id']
        request.urlconf = self.LANDING_URLCONF
        self._touch_last_seen(row)

        return self.get_response(request)

    @staticmethod
    def _touch_last_seen(row):
        """Record that traffic arrived for this host, at most once per window."""
        from django.core.cache import cache

        from .models import LandingDomain

        key = f"landing_domain_seen:{row['domain']}"
        if cache.get(key):
            return
        cache.set(key, True, _SEEN_THROTTLE_SECONDS)
        # Never let bookkeeping cost a visitor their page.
        try:
            LandingDomain.objects.filter(pk=row['id']).update(last_seen_at=timezone.now())
        except Exception:  # pragma: no cover - diagnostic only
            logger.warning("Could not record last_seen_at for %s", row['domain'], exc_info=True)
