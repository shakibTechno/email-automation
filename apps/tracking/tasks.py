"""
Draining the collect buffer, and keeping the event tables from growing forever.

The prune task is not optional and not "phase 4". Nothing anywhere in this
project deletes a row on a schedule -- CELERY_BEAT_SCHEDULE had thirteen
entries and not one of them was a pruner -- and PageView in apps/landing_pages
has been growing unbounded since it shipped. Adding two more event tables
without one would turn a slow problem into three.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

# Chunked so a prune never takes a long lock on a table the collector is
# writing to.
PRUNE_CHUNK = 5_000


@shared_task
def drain_tracking_buffer():
    """Write buffered page views to the database."""
    from .services import drain_buffer

    total = 0
    # Several passes per tick, so a busy minute does not leave a backlog that
    # the next tick inherits.
    for _ in range(10):
        written = drain_buffer()
        total += written
        if not written:
            break
    if total:
        logger.info('Wrote %d tracked events', total)
    return total


@shared_task
def prune_tracked_events():
    """
    Delete events, visitors and landing-page views past the retention window.

    Identified visitors are kept: once a visitor is a contact, their history is
    CRM data rather than analytics. Anonymous ones are the majority and are
    what actually grows.
    """
    from apps.landing_pages.models import PageView

    from .models import TrackedEvent, Visitor

    days = getattr(settings, 'TRACKING_RETENTION_DAYS', 365)
    cutoff = timezone.now() - timedelta(days=days)
    deleted = {'events': 0, 'visitors': 0, 'page_views': 0}

    deleted['events'] = _delete_in_chunks(
        TrackedEvent.objects.filter(occurred_at__lt=cutoff)
    )
    deleted['visitors'] = _delete_in_chunks(
        Visitor.objects.filter(contact__isnull=True, last_seen_at__lt=cutoff)
    )
    # The same window, applied to the table that had this problem first.
    deleted['page_views'] = _delete_in_chunks(
        PageView.objects.filter(created_at__lt=cutoff)
    )

    if any(deleted.values()):
        logger.info('Pruned %s', deleted)
    return deleted


def _delete_in_chunks(queryset):
    total = 0
    while True:
        ids = list(queryset.values_list('pk', flat=True)[:PRUNE_CHUNK])
        if not ids:
            return total
        count, _ = queryset.model.objects.filter(pk__in=ids).delete()
        total += count
        if len(ids) < PRUNE_CHUNK:
            return total
