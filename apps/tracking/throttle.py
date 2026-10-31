"""
Rate limiting for the collector.

Keyed on the organization rather than the IP. An IP limit punishes a whole
office behind one NAT and a mobile carrier's whole subscriber base, while doing
nothing about a flood spread over many addresses. The site key is the thing
being abused, so the site key is the thing to limit.

Soft, not hard: over the limit the events are dropped and counted, and the
response is the same 204 as always. A 429 tells an abuser their flood is
working and tells a real visitor nothing they can act on.
"""
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Generous for a real site, small enough that one abusive free account cannot
# fill the buffer on its own.
PER_SITE_PER_MINUTE = 600
PER_IP_PER_MINUTE = 120


def over_limit(organization_id, request):
    if _bump(f'trk:s:{organization_id}') > PER_SITE_PER_MINUTE:
        logger.warning('Tracking rate limit hit for organization %s', organization_id)
        return True
    ip = _client_ip(request)
    return bool(ip) and _bump(f'trk:i:{organization_id}:{ip}') > PER_IP_PER_MINUTE


def _bump(key):
    """Count one request in the current minute window."""
    try:
        # add() only sets when absent, which is what starts the window; incr()
        # then counts within it.
        cache.add(key, 0, 60)
        return cache.incr(key)
    except Exception:
        # A cache that is down must not take the collector with it.
        return 0


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
