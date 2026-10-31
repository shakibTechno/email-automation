"""Scheduled pop-ups becoming live."""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def publish_due_popups():
    """
    Flip scheduled pop-ups to published once their start time arrives.

    Done here rather than by the website script treating `scheduled` as live,
    so "why is it not showing" has one answer and the status a marketer sees
    is the status that decides.
    """
    from .models import Popup

    due = Popup.objects.filter(
        status=Popup.STATUS_SCHEDULED,
        starts_at__lte=timezone.now(),
        deleted_at__isnull=True,
    )
    count = due.update(status=Popup.STATUS_PUBLISHED, updated_at=timezone.now())
    if count:
        logger.info('Published %d scheduled pop-up(s)', count)
    return count
