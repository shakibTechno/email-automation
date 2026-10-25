"""
Hostname handling for connected landing-page domains.

One place for the rules, because three callers need the same answers and a
disagreement between them is a security hole rather than a cosmetic bug:
the model's validation, the API serializer, and the middleware that decides
which tenant a request belongs to.
"""
import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache

# Deliberately strict: a label per dot, no underscores, no trailing dot, and a
# TLD of at least two letters. The value becomes a tenant identifier, so
# anything we cannot reason about confidently is refused rather than normalized
# into something surprising.
_HOSTNAME_RE = re.compile(
    r'\A(?=.{4,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\Z'
)

CACHE_PREFIX = 'landing_domain:'
CACHE_TTL = 300


def normalize_domain(value):
    """Lowercase, strip a scheme/path/port if someone pasted a URL."""
    if not value:
        return ''
    value = str(value).strip().lower().rstrip('.')
    if '//' in value:
        value = urlparse(value).netloc or value
    value = value.split('/')[0]
    # A pasted "example.com:443" should not become a distinct domain.
    if ':' in value:
        value = value.split(':', 1)[0]
    return value


def platform_hosts():
    """
    Hostnames that belong to the platform itself and must keep serving the app.

    Includes `backend`, the Docker-network name Caddy uses for its on-demand
    TLS callback — without it that callback would be rejected as an unknown
    host and no certificate would ever be issued.
    """
    hosts = set()
    for host in getattr(settings, 'PLATFORM_HOSTS', []) or []:
        normalized = normalize_domain(host)
        if normalized:
            hosts.add(normalized)
        elif host:
            # `localhost` and bare service names have no dot and so do not
            # survive normalize_domain's hostname shape; keep them as given.
            hosts.add(str(host).strip().lower())
    return hosts


def is_platform_host(host):
    host = normalize_domain(host) or str(host or '').strip().lower()
    return host in platform_hosts()


def reserved_domain_error(domain):
    """
    Why this domain may not be connected, or None when it may.

    Returns a message rather than raising so the model, the serializer and the
    tests all phrase the refusal identically.
    """
    if not domain:
        return 'Enter a domain.'
    if not _HOSTNAME_RE.match(domain):
        return (
            'Enter a valid domain such as go.example.com. '
            'Subdomains only — no scheme, port or path.'
        )
    if is_platform_host(domain):
        return 'That domain belongs to the platform and cannot be connected.'
    # A subdomain of a platform host would resolve here by accident and could be
    # used to borrow the platform's name.
    for host in platform_hosts():
        if '.' in host and domain.endswith(f'.{host}'):
            return 'That domain belongs to the platform and cannot be connected.'
    return None


def _cache_key(domain):
    return f'{CACHE_PREFIX}{domain}'


def resolve_domain(host):
    """
    The LandingDomain for this host, or None.

    Cached because it runs on every request to a connected domain, which is
    public traffic. Cached negatively as well: an unknown host is the common
    case for scanners, and each one would otherwise cost a query.
    Returns the id/organization fields the middleware needs, not the instance,
    so a stale cache cannot carry a stale model around the request.
    """
    domain = normalize_domain(host)
    if not domain:
        return None

    key = _cache_key(domain)
    cached = cache.get(key)
    if cached is not None:
        return cached or None

    from .models import LandingDomain

    row = (
        LandingDomain.objects
        .filter(domain=domain, organization__is_active=True)
        .values('id', 'domain', 'status', 'organization_id')
        .first()
    )
    # `False` distinguishes "looked up, nothing there" from "not looked up".
    cache.set(key, row or False, CACHE_TTL)
    return row


def forget_domain(domain):
    """Drop a cached lookup. Called whenever a domain row changes."""
    domain = normalize_domain(domain)
    if domain:
        cache.delete(_cache_key(domain))


def split_zone(domain):
    """
    Guess ('label', 'zone') for a hostname — what to type, and into which zone.

    DNS providers ask for the record name *relative to the zone*: Namecheap,
    Cloudflare and GoDaddy all append the domain to whatever is entered, so
    `landing.soha.systems` in a Host field becomes
    `landing.soha.systems.soha.systems`. Showing the full name with a copy
    button next to it invites exactly that, and did.

    The zone cut cannot be known without the public suffix list — `brand.co.uk`
    is two labels of suffix, `soha.systems` is one — so this assumes the common
    `label.domain.tld` shape and the caller shows the assumption alongside the
    answer, letting the customer correct it rather than trusting us silently.
    """
    labels = normalize_domain(domain).split('.')
    if len(labels) < 3:
        return '@', '.'.join(labels)
    return '.'.join(labels[:-2]), '.'.join(labels[-2:])


def doubled_name_candidate(domain):
    """
    The name a record ends up at when the full hostname is typed into a Host
    field: `landing.soha.systems` + zone `soha.systems`.

    Used to recognise that specific mistake and name it, instead of reporting
    the generic "does not resolve" that leaves someone re-reading a record
    which looks exactly right where they put it.
    """
    _, zone = split_zone(domain)
    if not zone or domain.endswith('.' + zone) is False:
        return None
    return f'{domain}.{zone}'


def resolves(hostname):
    """
    Whether a hostname resolves to an address, following any CNAME.

    `socket.getaddrinfo` rather than a DNS library: the question is only
    "does this name lead to an address", the stdlib answers it, and
    apps/email_config/services.py records why a dnspython-based check was
    removed from this codebase before.
    """
    import socket

    if not hostname:
        return False
    try:
        socket.getaddrinfo(hostname, None)
    except OSError:
        return False
    return True


# Google's DNS-over-HTTPS JSON endpoint. Used only to *explain* a failure, never
# to decide one: verification stays the real HTTPS fetch, because that is what a
# visitor's browser will do.
PUBLIC_DNS_URL = 'https://dns.google/resolve'
PUBLIC_DNS_TIMEOUT = 4


def published_publicly(hostname):
    """
    Whether a public resolver can see a record for this hostname.

    True/False, or None when we could not find out — and None must not be
    reported as either, because the point of this check is to distinguish "your
    record is missing" from "your record is fine and our resolver is stale".

    That distinction matters more than it looks. A customer who corrects a wrong
    record hits a negative cache: the previous NXDOMAIN is held for the zone's
    SOA minimum, an hour on many zones, during which this server still cannot
    resolve a name the rest of the world already can. Without this check the
    only message we could give them was "does not resolve, check the Host
    field" — advice to change something they had just got right.
    """
    import requests

    if not hostname:
        return None
    try:
        response = requests.get(
            PUBLIC_DNS_URL,
            params={'name': hostname, 'type': 'A'},
            timeout=PUBLIC_DNS_TIMEOUT,
            headers={'Accept': 'application/dns-json'},
        )
        if response.status_code != 200:
            return None
        payload = response.json()
    except Exception:
        return None

    # Status 3 is NXDOMAIN; 0 with an Answer means something is published.
    if payload.get('Status') == 3:
        return False
    return bool(payload.get('Answer'))
