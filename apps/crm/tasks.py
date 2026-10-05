"""
Celery tasks for the CRM & Pipeline app.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)


@shared_task(name='apps.crm.tasks.flag_rotting_deals')
def flag_rotting_deals():
    """
    Flag open deals as rotting when last_activity_at exceeds their threshold.
    Falls back to created_at when no activity has ever been logged.
    Runs via Celery Beat (daily).
    """
    from .models import Deal

    now = timezone.now()
    rotted, cleared = 0, 0

    open_deals = Deal.objects.filter(status='open').only(
        'id', 'last_activity_at', 'created_at', 'is_rotting', 'rotting_threshold_days'
    )

    ids_to_rot = []
    ids_to_clear = []

    for deal in open_deals:
        reference = deal.last_activity_at or deal.created_at
        threshold = timezone.timedelta(days=deal.rotting_threshold_days)
        should_rot = (now - reference) >= threshold

        if should_rot and not deal.is_rotting:
            ids_to_rot.append(deal.id)
        elif not should_rot and deal.is_rotting:
            ids_to_clear.append(deal.id)

    if ids_to_rot:
        rotted = Deal.objects.filter(id__in=ids_to_rot).update(is_rotting=True)

    if ids_to_clear:
        cleared = Deal.objects.filter(id__in=ids_to_clear).update(is_rotting=False)

    logger.info('flag_rotting_deals: flagged=%d, cleared=%d', rotted, cleared)
    return {'rotted': rotted, 'cleared': cleared}
