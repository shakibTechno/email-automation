"""
Connecting, verifying and retiring a customer's landing-page domain.
"""
import logging
import secrets
import socket

import requests
from django.db import transaction
from django.utils import timezone

from .domains import (
    doubled_name_candidate,
    forget_domain,
    normalize_domain,
    reserved_domain_error,
    resolves,
    split_zone,
)
from .models import LandingDomain

logger = logging.getLogger(__name__)

# Short on purpose: this runs inside a request when the customer presses
# "Check now", and a domain that is not pointed here will simply hang.
VERIFY_TIMEOUT_SECONDS = 8


class DomainError(Exception):
    """A refusal with a message meant for the customer."""


class LandingDomainService:
    """
    Verification is a single HTTPS fetch of the domain's own token, not a DNS
    query. If `https://<their domain>/.well-known/...` round-trips back to us
    with the right token, then their DNS points here, Caddy obtained a
    certificate, and a visitor's browser will succeed — which is the thing we
    actually need to know. A resolver answering with the right CNAME proves
    none of that.
    """

    @staticmethod
    def connect(organization, domain):
        """Attach a domain to an organization, or explain why not."""
        domain = normalize_domain(domain)

        error = reserved_domain_error(domain)
        if error:
            raise DomainError(error)

        existing = LandingDomain.objects.filter(domain=domain).first()
        if existing is not None:
            if existing.organization_id == organization.id:
                raise DomainError('That domain is already connected.')
            # Deliberately not "another organization has it": a tenant must not
            # be able to probe which domains other customers use.
            raise DomainError('That domain is not available.')

        row = LandingDomain.objects.create(organization=organization, domain=domain)
        forget_domain(domain)
        logger.info("Connected landing domain %s to org %s", domain, organization.id)
        return row

    @staticmethod
    @transaction.atomic
    def set_primary(landing_domain):
        """
        Make this the organization's default domain.

        `is_primary` is cleared on the others in the same transaction, because
        two primaries would make `LandingPage.serving_domain` depend on row
        order — a page's public address silently deciding itself.
        """
        LandingDomain.objects.filter(
            organization_id=landing_domain.organization_id,
        ).exclude(pk=landing_domain.pk).update(is_primary=False)
        LandingDomain.objects.filter(pk=landing_domain.pk).update(is_primary=True)
        landing_domain.refresh_from_db()
        forget_domain(landing_domain.domain)
        return landing_domain

    @staticmethod
    def verify(landing_domain):
        """
        Fetch the domain's token over its own hostname and record the verdict.

        Never raises: this is called from a request handler and from a periodic
        task, and a network failure is a result ("not yet") rather than an
        error.
        """
        now = timezone.now()
        url = landing_domain.verification_url
        error = ''

        try:
            response = requests.get(
                url,
                timeout=VERIFY_TIMEOUT_SECONDS,
                # A redirect would mean the hostname is served by something
                # other than us; following one could make someone else's 200
                # look like ours.
                allow_redirects=False,
                headers={'User-Agent': 'MailFlow-Domain-Verification/1.0'},
            )
        except requests.exceptions.SSLError:
            error = (
                'The domain resolved but the HTTPS certificate is not ready yet. '
                'This usually clears within a minute of the DNS record going live.'
            )
        except requests.exceptions.ConnectionError as exc:
            # "Does not resolve" and "resolves but refuses the connection" are
            # different problems with different fixes, and conflating them cost
            # a customer three hours of waiting for propagation of a record
            # that had never been accepted. Say which it is.
            if _is_dns_failure(exc):
                error = _resolution_failure_message(landing_domain)
            else:
                error = (
                    'The hostname resolves but refused the connection. It is '
                    'probably pointing somewhere other than this platform.'
                )
        except requests.exceptions.Timeout:
            error = 'The domain did not respond in time.'
        except requests.RequestException as exc:  # pragma: no cover - defensive
            error = f'Could not verify the domain: {exc.__class__.__name__}.'
        else:
            if response.status_code != 200:
                error = (
                    'The domain is reachable but did not return the verification '
                    f'token (HTTP {response.status_code}). It may be pointing at '
                    'another service.'
                )
            elif not secrets.compare_digest(
                response.text.strip(), landing_domain.verification_token
            ):
                error = (
                    'The domain is reachable but another service answered for it. '
                    'Check that the CNAME record points at the value shown here.'
                )

        verified = not error
        LandingDomain.objects.filter(pk=landing_domain.pk).update(
            status=(
                LandingDomain.STATUS_VERIFIED if verified else LandingDomain.STATUS_FAILED
            ),
            # Kept from a previous success: a domain that verified once and is
            # momentarily unreachable has not become unverified.
            verified_at=now if verified else landing_domain.verified_at,
            last_check_at=now,
            last_check_error=error,
        )
        landing_domain.refresh_from_db()
        forget_domain(landing_domain.domain)

        logger.info(
            "Verification for %s: %s", landing_domain.domain,
            'ok' if verified else error,
        )
        return landing_domain

    @staticmethod
    @transaction.atomic
    def disconnect(landing_domain):
        """
        Remove a domain, promoting another to primary if this was it.

        Pages pinned to it fall back to the organization's primary through
        `on_delete=SET_NULL`, so removing a domain never takes a page offline
        beyond the address itself.
        """
        organization_id = landing_domain.organization_id
        was_primary = landing_domain.is_primary
        domain = landing_domain.domain

        landing_domain.delete()
        forget_domain(domain)

        if was_primary:
            replacement = LandingDomain.objects.filter(
                organization_id=organization_id
            ).order_by('-status', 'created_at').first()
            if replacement is not None:
                LandingDomainService.set_primary(replacement)


def _is_dns_failure(exc):
    """
    Whether a ConnectionError was name resolution failing, not a refused socket.

    requests wraps urllib3 wraps socket, so the useful detail is in the chain of
    causes rather than on the exception itself. Matching on the text is crude,
    but the alternative is resolving the name ourselves just to classify an
    error we have already hit.
    """
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, socket.gaierror):
            return True
        text = str(current).lower()
        if any(
            marker in text for marker in (
                'name or service not known',
                'nodename nor servname',
                'temporary failure in name resolution',
                'failed to resolve',
                'name resolution',
                'getaddrinfo failed',
                'no address associated with hostname',
            )
        ):
            return True
        current = current.__cause__ or current.__context__
    return False


def _resolution_failure_message(landing_domain):
    """
    Why the hostname does not resolve, as specifically as we can tell.

    "No DNS record found" is true but unhelpful when the record *was* saved and
    the provider silently put it somewhere else. Checking for the doubled name
    turns a customer re-reading a correct-looking record into a customer who
    knows which field to change.
    """
    domain = landing_domain.domain
    label, zone = split_zone(domain)

    doubled = doubled_name_candidate(domain)
    if doubled and resolves(doubled):
        return (
            f'Your DNS record was created as "{doubled}" rather than "{domain}". '
            f'Most providers add your domain to the Host field automatically, so '
            f'enter just "{label}" there — not the full "{domain}".'
        )

    message = (
        f'"{domain}" does not resolve — no DNS record for it was found. '
        f'In your DNS provider the Host (or Name) field should be "{label}", '
        f'not the full "{domain}", because the provider adds "{zone}" itself.'
    )
    if landing_domain.conflicting_sending_domain:
        message += (
            ' Note this hostname also sends your email, so it cannot take a '
            'CNAME — use the A record.'
        )
    return message
