"""
Applying Postal delivery events to campaign and sequence records.

Events are matched on the postal_id / postal_token captured at send time.
Postal does not echo custom headers, so those two values are the only reliable
link between a webhook and the row that produced it.
"""
import logging
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

from .postal_client import normalize_event

logger = logging.getLogger(__name__)

# Postal reports a temporary failure two ways: a MessageDelayed event, and a
# MessageDeliveryFailed whose payload status is SoftFail. Only a hard failure
# should bounce a contact out of future campaigns.
_SOFT_FAILURE_STATUSES = frozenset({'SoftFail', 'Softfail', 'softfail'})


def _event_time(value):
    """Convert Postal's float epoch timestamp to an aware datetime."""
    try:
        return datetime.fromtimestamp(float(value), tz=dt_timezone.utc)
    except (TypeError, ValueError):
        return timezone.now()


class PostalEventService:
    """Dispatches a normalized Postal event onto the right record."""

    @staticmethod
    def handle(body, tenant_hint=''):
        """
        Apply one webhook body. Returns a short string describing the outcome,
        which the Celery task logs.
        """
        event = normalize_event(body)
        if not event:
            return f"ignored:{body.get('event')}"

        if event['type'] == 'dns_error':
            return PostalEventService._handle_dns_error(event, tenant_hint)

        target, kind = PostalEventService._find_target(event)
        if target is None:
            # Normal for mail we did not send through a tracked record, e.g. the
            # configuration test send.
            logger.debug(
                'No record matched Postal event %s (id=%s)',
                event['type'], event.get('postal_id'),
            )
            return 'unmatched'

        handler = {
            'delivered': PostalEventService._handle_delivered,
            'deferred': PostalEventService._handle_deferred,
            'bounced': PostalEventService._handle_bounced,
            'held': PostalEventService._handle_held,
        }[event['type']]
        return handler(target, kind, event)

    # ------------------------------------------------------------------ matching
    @staticmethod
    def _find_target(event):
        """Locate the CampaignRecipient or SequenceStepExecution for an event."""
        from apps.campaigns.models import CampaignRecipient
        from apps.sequences.models import SequenceStepExecution

        postal_id = event.get('postal_id')
        token = event.get('token')

        for model, kind in ((CampaignRecipient, 'campaign'),
                            (SequenceStepExecution, 'sequence')):
            if postal_id:
                found = model.objects.filter(postal_id=postal_id).first()
                if found:
                    return found, kind
            if token:
                found = model.objects.filter(postal_token=token).first()
                if found:
                    return found, kind
        return None, None

    # ------------------------------------------------------------------ handlers
    @staticmethod
    def _handle_delivered(target, kind, event):
        at = _event_time(event.get('at'))
        if kind == 'campaign':
            target.advance_status('delivered', {'delivered_at': at})
        else:
            target.delivered_at = at
            target.save(update_fields=['delivered_at', 'updated_at'])
        return 'delivered'

    @staticmethod
    def _handle_deferred(target, kind, event):
        # Postal will retry on its own. Nothing to change; recording it would
        # only make a temporary blip look like a failure in the UI.
        logger.info(
            'Postal deferred a message to %s: %s',
            getattr(target, 'email', target.pk), event.get('details') or '',
        )
        return 'deferred'

    @staticmethod
    def _handle_bounced(target, kind, event):
        if event.get('status') in _SOFT_FAILURE_STATUSES:
            return PostalEventService._handle_deferred(target, kind, event)

        at = _event_time(event.get('at'))
        detail = (event.get('output') or event.get('details') or '')[:500]

        if kind == 'campaign':
            target.advance_status('bounced', {'bounced_at': at})
            contact = target.contact
            organization = target.campaign.organization
            address = target.email
        else:
            target.bounced_at = at
            target.status = 'failed'
            target.error_message = detail
            target.save(update_fields=[
                'bounced_at', 'status', 'error_message', 'updated_at',
            ])
            contact = target.enrollment.contact
            organization = target.enrollment.sequence.organization
            address = contact.email

        # Stops this contact being included in any future campaign: the
        # recipient query filters on bounced_at being null.
        if contact and not contact.bounced_at:
            contact.mark_bounced()

        # Postal suppresses hard bounces itself for 30 days; push it as well so
        # the suppression outlives that window and covers our own queueing.
        from .tasks import sync_suppression
        sync_suppression.delay(str(organization.id), address, 'hard_bounce')

        logger.info('Postal hard bounce for %s: %s', address, detail)
        return 'bounced'

    @staticmethod
    def _handle_held(target, kind, event):
        # Held means Postal refused to send: the tenant's send limit was hit, or
        # the address is on its suppression list. The mail is not lost, but it
        # will not move without intervention, so this must be visible.
        logger.warning(
            'Postal held a message to %s: %s',
            getattr(target, 'email', target.pk), event.get('details') or '',
        )
        return 'held'

    @staticmethod
    def _handle_dns_error(event, tenant_hint):
        """
        A sending domain's DNS broke.

        Re-running the check is what actually matters: it turns sending off for
        that domain until the record is fixed, rather than letting mail keep
        going out unauthenticated.
        """
        from .models import PostalTenant, SendingDomain
        from .provisioning import PostalProvisioningService

        domain_name = (event.get('domain') or '').lower()
        if not domain_name:
            return 'dns_error:no_domain'

        domains = SendingDomain.objects.filter(domain=domain_name)
        if tenant_hint:
            tenant = PostalTenant.objects.filter(external_id=tenant_hint).first()
            if tenant:
                domains = domains.filter(organization=tenant.organization)

        for domain in domains:
            try:
                PostalProvisioningService.check_domain(domain)
            except Exception:
                logger.exception('Re-check failed for domain %s after a DNS error', domain_name)
            logger.warning(
                'Postal reported a DNS error for %s (org %s): %s',
                domain_name, domain.organization_id, event.get('details') or '',
            )
        return 'dns_error'
