"""
Celery tasks for the integrations app.
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def sync_social_leads(integration_id):
    """Sync leads for a single social integration."""
    from .models import SocialIntegration
    from .services import LeadImportService

    try:
        integration = SocialIntegration.objects.get(id=integration_id)
    except SocialIntegration.DoesNotExist:
        logger.warning(f"SocialIntegration {integration_id} not found")
        return None

    sync_log = LeadImportService.import_leads(integration)
    logger.info(
        f"Sync completed for integration {integration_id}: "
        f"status={sync_log.status}, created={sync_log.leads_created}, "
        f"updated={sync_log.leads_updated}"
    )
    return str(sync_log.id)


@shared_task
def sync_all_auto_integrations():
    """
    Find all integrations with auto_sync=True, status='connected',
    and last_synced_at older than sync_interval_minutes (or never synced).
    Dispatch sync tasks for each.
    """
    from .models import SocialIntegration

    now = timezone.now()
    integrations = SocialIntegration.objects.filter(
        auto_sync=True,
        status='connected',
    )

    count = 0
    for integration in integrations:
        should_sync = False

        if integration.last_synced_at is None:
            should_sync = True
        else:
            next_sync_at = integration.last_synced_at + timedelta(
                minutes=integration.sync_interval_minutes
            )
            if now >= next_sync_at:
                should_sync = True

        if should_sync:
            sync_social_leads.delay(str(integration.id))
            count += 1

    if count:
        logger.info(f"Dispatched {count} auto-sync tasks")
    return count
