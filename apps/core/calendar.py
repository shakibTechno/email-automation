"""
One calendar over every date the product already keeps.

Campaigns, sequences, CRM activities, tasks and deals all carry their own
dates and their own machinery for acting on them. Nothing here schedules
anything: it reads those five sources into one shape and hands the writes back
to the endpoints that own them, so a rescheduled campaign goes through the same
field the wizard writes and the same Beat task picks it up.

Two rules this module exists to keep:

- **Volume is not events.** A sequence with 5,000 enrolments has 5,000 rows due
  on one day. They are counted in the query and returned as one chip per
  sequence per day, never as 5,000 events.
- **Every source is filtered by the viewer's own permission.** An aggregating
  endpoint is the classic place for a leak: one response quietly carrying five
  modules' data. A role without `campaigns.view` gets a calendar with no sends
  on it, and its filter is absent rather than empty.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.core import access

# A longer window would make the sequence aggregation read an unbounded slice
# of the execution table. Three months covers month, week and agenda views.
MAX_RANGE_DAYS = 92

# Campaign statuses worth a place on a calendar. Archived and cancelled ones
# carry old dates that would clutter the month they fell in.
CAMPAIGN_STATUSES = ('draft', 'scheduled', 'sending', 'paused', 'sent')
CAMPAIGN_MOVABLE_STATUSES = ('draft', 'scheduled')

# source key -> (label, permission to see it at all, permission to move it)
SOURCES = {
    'campaigns': ('Campaigns', 'campaigns.view', 'campaigns.edit'),
    'sequences': ('Sequences', 'sequences.view', None),
    'activities': ('Activities', 'crm.view', 'crm.edit'),
    'tasks': ('Tasks', 'crm.view', 'crm.edit'),
    'deals': ('Deal dates', 'crm.view', 'crm.edit'),
}


def viewer_timezone(user):
    """
    The timezone the viewer reads dates in.

    Day boundaries are the whole point: a campaign at 09:00 Dhaka belongs to
    that day in Dhaka, not to the previous one because the server runs in UTC.
    An unknown name falls back to UTC rather than failing the request.
    """
    try:
        return ZoneInfo(getattr(user, 'timezone', None) or 'UTC')
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo('UTC')


def resolve_range(user, start_date, end_date):
    """
    The half-open instant range for a pair of calendar dates, viewer-local.

    Returns (start, end, start_date, end_date): both the aware datetimes the
    timestamp columns are compared against and the plain dates the DateField
    columns are, since comparing a DateField against a UTC instant is what
    makes an all-day task drift a day.
    """
    tzinfo = viewer_timezone(user)
    today = timezone.now().astimezone(tzinfo).date()

    if start_date is None:
        start_date = today.replace(day=1)
    if end_date is None:
        # The last day of start_date's month.
        following = (start_date.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        end_date = following - dt.timedelta(days=1)

    start = dt.datetime.combine(start_date, dt.time.min, tzinfo=tzinfo)
    end = dt.datetime.combine(end_date, dt.time.max, tzinfo=tzinfo)
    return start, end, start_date, end_date


class CalendarService:
    """Reads the five sources into one list of events."""

    def __init__(self, user, start, end, start_date, end_date):
        self.user = user
        self.organization = user.organization
        self.start = start
        self.end = end
        self.start_date = start_date
        self.end_date = end_date
        self.tzinfo = viewer_timezone(user)

    # -- what this viewer may see ------------------------------------------

    def visible_sources(self):
        """The sources this viewer may see, in display order."""
        return [
            key for key, (_label, needed, _edit) in SOURCES.items()
            if access.has_permission(self.user, needed)
        ]

    def _can_move(self, key):
        _label, _needed, edit = SOURCES[key]
        return bool(edit) and access.has_permission(self.user, edit)

    # -- the payload -------------------------------------------------------

    def payload(self):
        """
        Every event in range this viewer may see, with a count per source.

        There is no source filter here on purpose: the whole range is a few
        hundred rows, so the chips filter what is already in the browser and
        toggle without a round trip -- and the counts stay honest, because they
        are taken from the events themselves rather than from a second query.
        """
        visible = self.visible_sources()
        builders = {
            'campaigns': self._campaigns,
            'sequences': self._sequences,
            'activities': self._activities,
            'tasks': self._tasks,
            'deals': self._deals,
        }

        events = []
        for key in visible:
            events.extend(builders[key]())

        events.sort(key=lambda e: (e['start'], e['title']))

        totals = {key: 0 for key in visible}
        for event in events:
            totals[event['source']] += 1

        return {
            'start': self.start_date.isoformat(),
            'end': self.end_date.isoformat(),
            'timezone': str(self.tzinfo),
            'sources': [
                {'key': key, 'label': SOURCES[key][0], 'count': totals.get(key, 0)}
                for key in self.visible_sources()
            ],
            'events': events,
        }

    # -- sources -----------------------------------------------------------

    def _local(self, moment):
        return moment.astimezone(self.tzinfo).isoformat()

    def _campaigns(self):
        from apps.campaigns.models import Campaign

        now = timezone.now()
        # One event per campaign, dated by when it actually went or will go.
        # Querying scheduled_at and sent_at as two sources would list a sent
        # campaign twice -- once on the day it was planned for, once on the day
        # it left.
        rows = (
            Campaign.objects
            .filter(organization=self.organization, status__in=CAMPAIGN_STATUSES)
            .filter(
                Q(sent_at__range=(self.start, self.end))
                | Q(scheduled_at__range=(self.start, self.end))
            )
            .only('id', 'name', 'status', 'scheduled_at', 'sent_at', 'recipient_count')
        )

        movable = self._can_move('campaigns')
        events = []
        for campaign in rows:
            when = campaign.sent_at or campaign.scheduled_at
            if when is None or not (self.start <= when <= self.end):
                continue
            events.append({
                'id': f'campaign:{campaign.id}',
                'source': 'campaigns',
                'title': campaign.name,
                'start': self._local(when),
                'end': None,
                'all_day': False,
                'status': campaign.status,
                'url': f'/campaigns/{campaign.id}',
                'movable': (
                    movable
                    and campaign.status in CAMPAIGN_MOVABLE_STATUSES
                    and when > now
                ),
                'meta': {'recipients': campaign.recipient_count},
            })
        return events

    def _sequences(self):
        from apps.sequences.models import SequenceStepExecution

        rows = (
            SequenceStepExecution.objects
            .filter(
                enrollment__sequence__organization=self.organization,
                status='pending',
                scheduled_at__range=(self.start, self.end),
            )
            # TruncDate with an explicit tzinfo, not `scheduled_at__date`:
            # that truncates in the connection's timezone, so a send at 01:00
            # Dhaka (19:00 UTC the day before) would be counted into the
            # previous day and the chip would sit on the wrong square.
            .annotate(day=TruncDate('scheduled_at', tzinfo=self.tzinfo))
            .values(
                'enrollment__sequence_id',
                'enrollment__sequence__name',
                'day',
            )
            .annotate(total=Count('id'))
            .order_by('day')
        )

        events = []
        for row in rows:
            day = row['day']
            sequence_id = row['enrollment__sequence_id']
            events.append({
                'id': f'sequence:{sequence_id}:{day.isoformat()}',
                'source': 'sequences',
                'title': row['enrollment__sequence__name'],
                'start': day.isoformat(),
                'end': None,
                'all_day': True,
                'status': 'pending',
                'url': f'/sequences/{sequence_id}',
                # A day's volume is the sum of thousands of per-contact rows.
                # There is no single thing to drag.
                'movable': False,
                'meta': {'emails': row['total']},
            })
        return events

    def _activities(self):
        from apps.crm.models import Activity

        rows = (
            Activity.objects
            .filter(organization=self.organization, due_date__range=(self.start, self.end))
            .select_related('deal')
            .only(
                'id', 'title', 'activity_type', 'due_date', 'duration',
                'is_completed', 'deal__id', 'deal__title',
            )
        )

        movable = self._can_move('activities')
        events = []
        for activity in rows:
            end = None
            if activity.duration:
                end = self._local(activity.due_date + dt.timedelta(minutes=activity.duration))
            events.append({
                'id': f'activity:{activity.id}',
                'source': 'activities',
                'title': activity.title,
                'start': self._local(activity.due_date),
                'end': end,
                'all_day': False,
                'status': 'completed' if activity.is_completed else 'open',
                'url': f'/crm/deals/{activity.deal_id}' if activity.deal_id else '/crm',
                'movable': movable and not activity.is_completed,
                'meta': {
                    'kind': activity.activity_type,
                    'duration': activity.duration,
                    'deal': activity.deal.title if activity.deal_id else None,
                },
            })
        return events

    def _tasks(self):
        from apps.crm.models import CRMTask

        rows = (
            CRMTask.objects
            .filter(
                organization=self.organization,
                due_date__range=(self.start_date, self.end_date),
            )
            .select_related('deal', 'assigned_to')
            .only(
                'id', 'title', 'status', 'priority', 'due_date',
                'deal__id', 'deal__title', 'assigned_to__first_name',
                'assigned_to__last_name', 'assigned_to__email',
            )
        )

        movable = self._can_move('tasks')
        return [
            {
                'id': f'task:{task.id}',
                'source': 'tasks',
                'title': task.title,
                'start': task.due_date.isoformat(),
                'end': None,
                'all_day': True,
                'status': task.status,
                'url': f'/crm/deals/{task.deal_id}' if task.deal_id else '/crm/tasks',
                'movable': movable and task.status != 'done',
                'meta': {
                    'priority': task.priority,
                    'deal': task.deal.title if task.deal_id else None,
                    'assignee': task.assigned_to.full_name if task.assigned_to_id else None,
                },
            }
            for task in rows
        ]

    def _deals(self):
        from apps.crm.models import Deal

        rows = (
            Deal.objects
            .filter(
                organization=self.organization,
                status='open',
                close_date__range=(self.start_date, self.end_date),
            )
            .only('id', 'title', 'value', 'currency', 'close_date')
        )

        movable = self._can_move('deals')
        return [
            {
                'id': f'deal:{deal.id}',
                'source': 'deals',
                'title': deal.title,
                'start': deal.close_date.isoformat(),
                'end': None,
                'all_day': True,
                'status': 'open',
                'url': f'/crm/deals/{deal.id}',
                'movable': movable,
                'meta': {'value': str(deal.value), 'currency': deal.currency},
            }
            for deal in rows
        ]
