"""
The certificate-issuance gate for Caddy's on-demand TLS.

Caddy asks this endpoint before obtaining a certificate for a hostname it has
never seen. 2xx means "go ahead", anything else means "refuse". It is therefore
the only thing standing between a stranger pointing DNS at this server and our
Let's Encrypt account's rate limit — which is per-account and takes a week to
recover from.

**This must not be reachable from the public internet.** It is mounted under
`/internal/`, a prefix absent from `frontend/nginx.conf`'s proxied-path regex
and from `config.urls_landing`, so the only route to it is Caddy talking to
`backend:8000` over the Docker network. Adding `internal` to either of those
places would open it.

Answering for *registered* domains rather than only verified ones is safe and
deliberate: ACME requires answering a challenge on the hostname itself, which
requires the DNS to already point here. Someone registering a domain they do not
control gets no certificate, because they get no traffic.
"""
import logging

from django.http import HttpResponse
from django.views.decorators.http import require_GET

from .domains import is_platform_host, normalize_domain, resolve_domain

logger = logging.getLogger(__name__)


@require_GET
def tls_allow(request):
    """Answer 200 if `?domain=` may be issued a certificate, else 404."""
    domain = normalize_domain(request.GET.get('domain', ''))

    if not domain:
        return HttpResponse(status=404)

    # The platform's own hostname is handled by its explicit Caddy site block,
    # but answering for it here too keeps a reconfiguration from locking us out.
    if is_platform_host(domain):
        return HttpResponse(status=200)

    row = resolve_domain(domain)
    if row is None:
        # Logged because a burst of these is the signature of someone pointing
        # DNS at this server, which is worth noticing before it costs a quota.
        logger.info("Refused certificate for unconnected domain %r", domain[:200])
        return HttpResponse(status=404)

    return HttpResponse(status=200)
