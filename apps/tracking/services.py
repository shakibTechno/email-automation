"""
Collecting page views, and turning a visitor into a contact.

The request path does no database work. A collect request validates, pushes
onto a Redis list and returns 204; a beat task drains that list in batches.
`apps/email_config/webhooks.py` is the precedent for acking fast, but not for
queueing: it fires one Celery task per event, which is right at email volume
and wrong at web volume, where per-task broker overhead would saturate a worker
on bookkeeping alone.
"""
import json
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import TrackedEvent, Visitor

logger = logging.getLogger(__name__)

BUFFER_KEY = 'tracking:events'
# The buffer is capped so a flood cannot grow the queue until Redis runs out of
# memory -- and Redis here is both the cache and the Celery broker, so that
# failure takes the whole platform with it, not just tracking.
BUFFER_MAX = 50_000
DRAIN_BATCH = 1_000

MAX_EVENTS_PER_REQUEST = 20
MAX_BODY_BYTES = 16 * 1024

# How far back an identification reaches. A visitor who has been reading for a
# year should not have the whole year attributed in one write.
BACKFILL_DAYS = 90
BACKFILL_LIMIT = 500


def _redis():
    """
    The raw client, for the list operations the cache API does not expose.

    Returns None where the cache is not Redis -- tests and any deployment
    using locmem. The fallback below is not atomic, which is fine for those
    and would not be for production, where Redis is both the cache and the
    Celery broker.
    """
    try:
        from django_redis import get_redis_connection
        return get_redis_connection('default')
    except Exception:
        return None


def buffer_events(organization_id, events):
    """Push validated events onto the buffer. Returns how many were accepted."""
    if not events:
        return 0
    payload = [
        json.dumps({'org': str(organization_id), **event}, separators=(',', ':'))
        for event in events
    ]
    client = _redis()
    try:
        if client is not None:
            length = client.rpush(BUFFER_KEY, *payload)
            if length > BUFFER_MAX:
                # Drop the oldest rather than refuse the newest: under a flood
                # the recent events are the ones worth keeping, and an
                # unbounded list is the failure that matters -- Redis here is
                # also the Celery broker, so filling it takes the platform.
                client.ltrim(BUFFER_KEY, -BUFFER_MAX, -1)
                logger.warning('Tracking buffer over %d; oldest dropped', BUFFER_MAX)
        else:
            queued = (cache.get(BUFFER_KEY) or []) + payload
            cache.set(BUFFER_KEY, queued[-BUFFER_MAX:], None)
        return len(payload)
    except Exception:
        # Losing a page view is not worth a 500 to a visitor's browser.
        logger.exception('Could not buffer tracking events')
        return 0


def drain_buffer(limit=DRAIN_BATCH):
    """
    Write buffered events to the database. Returns how many were written.

    Called by a beat task, so it is the only thing that writes events and the
    only place the per-visitor counters move.
    """
    client = _redis()
    try:
        if client is not None:
            raw = client.lpop(BUFFER_KEY, limit)
        else:
            queued = cache.get(BUFFER_KEY) or []
            raw, rest = queued[:limit], queued[limit:]
            cache.set(BUFFER_KEY, rest, None)
    except Exception:
        logger.exception('Could not read the tracking buffer')
        return 0
    if not raw:
        return 0

    rows = []
    for item in raw:
        try:
            rows.append(json.loads(item))
        except (TypeError, ValueError):
            continue

    return _write(rows)


@transaction.atomic
def _write(rows):
    from apps.accounts.models import Organization

    # Group by (organization, visitor) so each visitor is resolved once rather
    # than once per page view.
    by_visitor = {}
    for row in rows:
        key = (row.get('org'), row.get('vid'))
        if not all(key):
            continue
        by_visitor.setdefault(key, []).append(row)

    org_ids = {org_id for org_id, _ in by_visitor}
    known = set(
        Organization.objects.filter(id__in=org_ids).values_list('id', flat=True)
    )

    events = []
    popup_tally = {}
    for (org_id, visitor_key), items in by_visitor.items():
        if org_id not in {str(i) for i in known}:
            continue
        visitor, _ = Visitor.objects.get_or_create(
            organization_id=org_id, visitor_id=visitor_key,
        )
        latest = visitor.last_seen_at
        for item in items:
            occurred = parse_datetime(item.get('at') or '') or timezone.now()
            if timezone.is_naive(occurred):
                occurred = timezone.make_aware(occurred)
            latest = max(latest, occurred) if latest else occurred
            event_type = item.get('t') or TrackedEvent.EVENT_PAGEVIEW
            popup_id = item.get('pu') or None
            if event_type in TrackedEvent.POPUP_EVENTS:
                # A popup event naming a popup this key does not own is
                # dropped rather than written against the wrong tenant.
                if popup_id not in owned_popups(org_id):
                    continue
                popup_tally[(org_id, popup_id, event_type)] = (
                    popup_tally.get((org_id, popup_id, event_type), 0) + 1
                )
            else:
                popup_id = None
            events.append(TrackedEvent(
                organization_id=org_id,
                visitor=visitor,
                contact=visitor.contact,
                event_type=event_type,
                popup_id=popup_id,
                url=(item.get('u') or '')[:2000],
                path=(item.get('p') or '')[:500],
                title=(item.get('ti') or '')[:255],
                referrer=(item.get('r') or '')[:2000],
                occurred_at=occurred,
            ))
        Visitor.objects.filter(pk=visitor.pk).update(
            last_seen_at=latest or timezone.now(),
            page_view_count=models_f_add(visitor, len(items)),
        )
        _touch_contact_activity(visitor)
        _score_page_view(visitor)
        _fire_popup_workflows(visitor, items)

    if events:
        TrackedEvent.objects.bulk_create(events, batch_size=500)
    _apply_popup_tally(popup_tally)
    return len(events)


def owned_popups(org_id):
    """The popup ids this organization owns, cached briefly."""
    key = f'tracking:popups:{org_id}'
    ids = cache.get(key)
    if ids is None:
        from apps.popups.models import Popup
        ids = {
            str(pk) for pk in
            Popup.objects.filter(organization_id=org_id).values_list('id', flat=True)
        }
        cache.set(key, ids, 300)
    return ids


COUNTER_FOR = {
    TrackedEvent.EVENT_POPUP_SHOWN: 'impression_count',
    TrackedEvent.EVENT_POPUP_CLICKED: 'click_count',
}


def _apply_popup_tally(tally):
    """
    Move the cached counters once per batch.

    One UPDATE per popup per drain rather than per event: these are the
    highest-volume writes in the project and a read-modify-write per
    impression would both be slow and lose counts under concurrency.
    """
    from django.db.models import F

    from apps.popups.models import Popup

    totals = {}
    for (_org_id, popup_id, event_type), count in tally.items():
        field = COUNTER_FOR.get(event_type)
        if field:
            totals.setdefault(popup_id, {}).setdefault(field, 0)
            totals[popup_id][field] += count

    for popup_id, fields in totals.items():
        Popup.objects.filter(pk=popup_id).update(**{
            name: F(name) + amount for name, amount in fields.items()
        })


def models_f_add(visitor, count):
    """`F()` expression for the counter, kept readable at the call site."""
    from django.db.models import F
    return F('page_view_count') + count


def _touch_contact_activity(visitor):
    """
    Move `Contact.last_activity_at`, at most once an hour per visitor.

    `update_activity()` is one UPDATE per call, and this is the
    highest-volume path in the project. The cache guard is the same shape as
    LandingHostMiddleware._touch_last_seen.
    """
    if visitor.contact_id is None:
        return
    key = f'tracking:activity:{visitor.contact_id}'
    if not cache.add(key, '1', 3600):
        return
    try:
        visitor.contact.update_activity()
    except Exception:
        logger.exception('Could not stamp last_activity_at')


def identify(organization, visitor_key, contact):
    """
    Link a visitor to a contact, and backfill what they read before.

    Only ever called from a server-side event that already knows the contact —
    today, a form submission. Nothing a browser claims reaches here: a client
    that could name its own contact would be an email-enumeration oracle, and
    could attach an invented history to a real person, which feeds lead scores
    and segments and therefore sends.
    """
    if not (visitor_key and contact):
        return None

    visitor, _ = Visitor.objects.get_or_create(
        organization=organization, visitor_id=visitor_key,
    )
    if visitor.contact_id and visitor.contact_id != contact.id:
        # A shared browser. Keep the first identification rather than letting
        # the second rewrite the first's history.
        logger.info(
            'Visitor %s already identified as %s; not relinking',
            visitor_key, visitor.contact_id,
        )
        return visitor

    if visitor.contact_id is None:
        visitor.contact = contact
        visitor.identified_at = timezone.now()
        visitor.save(update_fields=['contact', 'identified_at', 'updated_at'])

        cutoff = timezone.now() - timedelta(days=BACKFILL_DAYS)
        backfill = list(
            TrackedEvent.objects
            .filter(visitor=visitor, contact__isnull=True, occurred_at__gte=cutoff)
            .order_by('-occurred_at')
            .values_list('id', flat=True)[:BACKFILL_LIMIT]
        )
        if backfill:
            TrackedEvent.objects.filter(id__in=backfill).update(contact=contact)
            logger.info(
                'Backfilled %d events onto contact %s', len(backfill), contact.id
            )
    return visitor


def _score_page_view(visitor):
    """
    Let a `page_viewed` scoring rule fire, at most once per contact per day.

    Without the cap this is the project's highest-volume path multiplied by
    the number of matching rules, each ending in a Contact write. A visitor
    reading twenty pages is one interested person, not twenty events worth of
    score.
    """
    if visitor.contact_id is None:
        return
    key = f'tracking:score:{visitor.contact_id}'
    if not cache.add(key, '1', 86400):
        return
    try:
        from apps.lead_scoring.signals import _fire_behavioral_rules
        from apps.lead_scoring.models import ScoringRule

        _fire_behavioral_rules(visitor.contact, ScoringRule.EVENT_PAGE_VIEWED)
    except Exception:
        logger.exception('Could not score a page view')


def _fire_popup_workflows(visitor, items):
    """
    Let a workflow react to a pop-up being shown or clicked.

    Only for an identified visitor: a workflow acts on a contact, and most
    people who see a pop-up are nobody yet. Capped per contact per popup per
    day for the same reason page-view scoring is -- this is a high-volume
    path and a workflow is an expensive thing to start twice.
    """
    if visitor.contact_id is None:
        return

    from apps.tracking.models import TrackedEvent

    wanted = {
        TrackedEvent.EVENT_POPUP_SHOWN: 'trigger_popup_shown',
        TrackedEvent.EVENT_POPUP_CLICKED: 'trigger_popup_clicked',
    }
    seen = set()
    for item in items:
        node_type = wanted.get(item.get('t'))
        popup_id = item.get('pu')
        if not node_type or not popup_id or (node_type, popup_id) in seen:
            continue
        seen.add((node_type, popup_id))

        key = f'tracking:popupwf:{visitor.contact_id}:{popup_id}:{node_type}'
        if not cache.add(key, '1', 86400):
            continue
        try:
            from apps.popups.models import Popup
            from apps.workflows.services import WorkflowTriggerService

            popup = Popup.objects.filter(pk=popup_id).first()
            if popup:
                WorkflowTriggerService.trigger_popup_interaction(
                    popup, visitor.contact, node_type,
                )
        except Exception:
            logger.exception('Could not fire popup workflows')
