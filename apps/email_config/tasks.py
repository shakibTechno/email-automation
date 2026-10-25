"""
Celery tasks for Postal provisioning, webhooks and guardrails.

Follows the coordinator/fan-out convention used elsewhere in this project
(see apps/lead_scoring/tasks.py): a periodic task queries organizations and
queues one child task per organization with a stringified UUID, and the child
re-fetches by primary key and treats DoesNotExist as terminal.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────── webhooks
@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_postal_event(self, body, tenant_hint=''):
    """
    Apply one Postal webhook, queued by the receiving view.

    The view has already verified the signature and de-duplicated on the event
    uuid, so this runs exactly once per genuine event.
    """
    from .events import PostalEventService

    try:
        outcome = PostalEventService.handle(body, tenant_hint)
        logger.debug('Postal event %s -> %s', body.get('event'), outcome)
        return outcome
    except Exception as exc:
        logger.exception('Failed to process Postal event %s', body.get('uuid'))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_suppression(self, organization_id, address, reason='platform'):
    """
    Add an address to the organization's Postal suppression list.

    Postal suppresses hard bounces itself for 30 days. Pushing unsubscribes and
    complaints as well means the suppression outlives that window, and protects
    the shared IP even if our own queueing has a bug.
    """
    from apps.accounts.models import Organization
    from .provisioner_client import ProvisionerError, get_provisioner
    from .provisioning import PostalProvisioningService

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        return 'organization_missing'

    tenant = PostalProvisioningService.get_tenant(organization)
    if not tenant or not tenant.postal_tenant_id:
        return 'no_tenant'

    try:
        get_provisioner().suppress(tenant.postal_tenant_id, address, reason=reason)
    except ProvisionerError as exc:
        if exc.code in ('not_configured', 'invalid_address'):
            return f'skipped:{exc.code}'
        raise self.retry(exc=exc)
    return 'suppressed'


# ──────────────────────────────────────────────────────────────────── domains
@shared_task
def recheck_pending_domains():
    """
    Re-run DNS checks for domains that are not yet sending.

    DNS changes take minutes to hours to propagate, so a customer who has just
    pasted their records should not have to keep pressing Verify. Checks stop
    after 72 hours; past that the records are not coming and the customer needs
    to look at the errors rather than have us keep polling.
    """
    from .models import SendingDomain
    from .provisioning import PostalProvisioningService

    cutoff = timezone.now() - timedelta(hours=72)
    pending = SendingDomain.objects.filter(
        sending_enabled=False, created_at__gte=cutoff,
    ).select_related('organization')

    checked = enabled = 0
    for domain in pending:
        try:
            ok, _ = PostalProvisioningService.check_domain(domain)
            checked += 1
            if ok:
                enabled += 1
                _notify_domain_verified(domain)
        except Exception:
            logger.exception('Re-check failed for domain %s', domain.domain)
    return {'checked': checked, 'enabled': enabled}


def _notify_domain_verified(domain):
    try:
        from apps.notifications.services import NotificationService
        NotificationService.notify_org_admins(
            organization=domain.organization,
            notification_type='sending_domain_verified',
            title='Sending domain verified',
            message=f'{domain.domain} passed all DNS checks and can now send email.',
            data={'domain': domain.domain},
        )
    except Exception:
        logger.exception('Could not notify admins that %s verified', domain.domain)


# ───────────────────────────────────────────────────────────────── guardrails
@shared_task
def evaluate_all_guardrails():
    """
    Coordinator: check every organization that has sent recently.

    Scoped to organizations with a Postal tenant, since an organization using
    its own ESP is not sending from the shared IP this protects.
    """
    from .models import PostalTenant

    org_ids = (
        PostalTenant.objects
        .exclude(postal_tenant_id='')
        .filter(organization__is_active=True, organization__deleted_at__isnull=True)
        .values_list('organization_id', flat=True)
    )
    count = 0
    for org_id in org_ids:
        evaluate_organization_guardrails.delay(str(org_id))
        count += 1
    logger.info('Queued guardrail checks for %s organizations', count)
    return count


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def evaluate_organization_guardrails(self, organization_id):
    """Measure one organization's bounce/complaint rates and pause if breached."""
    from apps.accounts.models import Organization
    from .guardrails import evaluate

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        return 'organization_missing'

    try:
        return evaluate(organization)
    except Exception as exc:
        logger.exception('Guardrail evaluation failed for org %s', organization_id)
        raise self.retry(exc=exc)


@shared_task
def sync_postal_tenants():
    """Refresh cached Postal metrics (queued, held, bounce_rate_30d) for all tenants."""
    from .guardrails import sync_all_tenants
    return sync_all_tenants()
