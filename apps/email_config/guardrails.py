"""
Deliverability guardrails.

Every organization sends from the same server, so they share one IP reputation:
one customer mailing a bought list can get that IP blocked at Gmail or
Microsoft for everyone else. These checks are what stop that, and they are the
reason mailstack/MULTI-TENANT.md §6 calls them day-one work rather than
something to retrofit.

EmailConfiguration already carries bounce_threshold_pct and
complaint_threshold_pct, and check_sending_limits() already refuses to send
when sending_paused_due_to_threshold is set — but nothing ever set that flag.
This module closes that loop and suspends the Postal tenant alongside it, so
mail stops at the server too rather than only in our own queue.
"""
import logging
from datetime import timedelta

from django.utils import timezone

from .models import EmailConfiguration, PostalTenant
from .provisioner_client import ProvisionerError
from .provisioning import PostalProvisioningService

logger = logging.getLogger(__name__)

# How far back to measure. Long enough to be meaningful, short enough that a
# cleaned-up list lets a customer recover without waiting a month.
WINDOW_DAYS = 7

# Below this many sends the rates are noise: two bounces out of three sends is
# 67% and means nothing. Without a floor, every new customer's first test send
# would suspend them.
MIN_VOLUME = 50


def measure(organization, window_days=WINDOW_DAYS):
    """
    Return bounce and complaint rates for an organization's recent sending.

    Rates are a percentage of messages actually sent in the window.
    """
    from apps.campaigns.models import CampaignRecipient

    since = timezone.now() - timedelta(days=window_days)
    recipients = CampaignRecipient.objects.filter(
        campaign__organization=organization, sent_at__gte=since,
    )

    sent = recipients.count()
    if not sent:
        return {'sent': 0, 'bounced': 0, 'complained': 0,
                'bounce_rate': 0.0, 'complaint_rate': 0.0}

    bounced = recipients.filter(bounced_at__isnull=False).count()
    complained = recipients.filter(complained_at__isnull=False).count()
    return {
        'sent': sent,
        'bounced': bounced,
        'complained': complained,
        'bounce_rate': round(bounced / sent * 100, 2),
        'complaint_rate': round(complained / sent * 100, 2),
    }


def evaluate(organization):
    """
    Measure an organization and pause its sending if it has breached a threshold.

    Returns a dict describing what was found and whether action was taken.
    Deliberately does not auto-resume: a breach needs a human to look at the
    list before mail starts flowing again, which is what the resume endpoint is
    for.
    """
    metrics = measure(organization)
    result = {'organization_id': str(organization.id), **metrics, 'action': 'none'}

    if metrics['sent'] < MIN_VOLUME:
        result['action'] = 'skipped_low_volume'
        return result

    config = EmailConfiguration.objects.filter(organization=organization).first()
    if not config:
        return result

    bounce_limit = float(config.bounce_threshold_pct or 0)
    complaint_limit = float(config.complaint_threshold_pct or 0)

    reasons = []
    if bounce_limit and metrics['bounce_rate'] > bounce_limit:
        reasons.append(
            f"bounce rate {metrics['bounce_rate']}% over the {bounce_limit}% limit"
        )
    if complaint_limit and metrics['complaint_rate'] > complaint_limit:
        reasons.append(
            f"complaint rate {metrics['complaint_rate']}% over the {complaint_limit}% limit"
        )

    if not reasons:
        return result

    reason = '; '.join(reasons)
    result['reason'] = reason

    if not config.sending_paused_due_to_threshold:
        config.sending_paused_due_to_threshold = True
        config.save(update_fields=['sending_paused_due_to_threshold', 'updated_at'])
        logger.warning('Paused sending for org %s: %s', organization.id, reason)

    tenant = PostalProvisioningService.get_tenant(organization)
    if tenant and tenant.postal_tenant_id and not tenant.is_suspended:
        try:
            PostalProvisioningService.suspend(tenant, reason)
            result['action'] = 'paused_and_suspended'
        except ProvisionerError as exc:
            # The local pause still holds, so no mail goes out from our queue.
            logger.error(
                'Paused org %s locally but could not suspend its tenant: %s',
                organization.id, exc,
            )
            result['action'] = 'paused_suspend_failed'
    else:
        result['action'] = 'paused'

    _notify_admins(organization, reason)
    return result


def _notify_admins(organization, reason):
    """Tell the organization's admins that sending stopped, and why."""
    try:
        from apps.notifications.services import NotificationService
        NotificationService.notify_org_admins(
            organization,
            'sending_paused',
            'Sending paused',
            f'Email sending was paused automatically: {reason}. '
            'Review your contact list, then resume from Settings → Email.',
        )
    except Exception:
        # Never let a notification failure undo the pause.
        logger.exception('Could not notify admins about the sending pause')


def sync_all_tenants():
    """Refresh cached Postal metrics for every provisioned tenant."""
    synced, failed = 0, 0
    tenants = PostalTenant.objects.exclude(postal_tenant_id='').select_related('organization')
    for tenant in tenants:
        try:
            PostalProvisioningService.sync_tenant(tenant)
            synced += 1
        except ProvisionerError as exc:
            failed += 1
            logger.warning('Could not sync tenant %s: %s', tenant.external_id, exc)
    return {'synced': synced, 'failed': failed}
