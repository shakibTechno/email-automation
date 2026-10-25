"""
Background work for connected landing-page domains.
"""
import logging

from celery import shared_task
from django.utils import timezone

from .domain_service import LandingDomainService
from .models import LandingDomain

logger = logging.getLogger(__name__)

# How long a domain stays worth re-checking on its own. A customer who adds a
# CNAME takes minutes to hours; one who adds a domain and never touches DNS
# should not be polled forever.
RECHECK_WINDOW_DAYS = 14


@shared_task(name='apps.landing_pages.tasks.recheck_pending_domains')
def recheck_pending_domains():
    """
    Re-verify domains that are not yet serving.

    Customers publish the DNS record and then go away; without this they would
    have to come back and press a button to be told it worked. Verified domains
    are left alone — a page going down is not something this task can fix, and
    re-checking them would turn a transient network blip into a "failed" badge
    on a domain that is fine.
    """
    cutoff = timezone.now() - timezone.timedelta(days=RECHECK_WINDOW_DAYS)

    pending = LandingDomain.objects.filter(
        status__in=[LandingDomain.STATUS_PENDING, LandingDomain.STATUS_FAILED],
        created_at__gte=cutoff,
        organization__is_active=True,
    )

    checked = verified = 0
    for domain in pending:
        checked += 1
        try:
            result = LandingDomainService.verify(domain)
        except Exception:  # pragma: no cover - one bad row must not stop the rest
            logger.warning("Could not verify %s", domain.domain, exc_info=True)
            continue
        if result.is_verified:
            verified += 1

    logger.info("Re-checked %s pending landing domains, %s verified", checked, verified)
    return {'checked': checked, 'verified': verified}
