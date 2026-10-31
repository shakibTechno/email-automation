"""Numbers for one pop-up, and the status a schedule implies."""
import logging
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

logger = logging.getLogger(__name__)


class PopupAnalyticsService:
    """
    Follows apps/analytics/services.py: read-only aggregation, computed per
    request from the event table rather than stored.

    The cached counters on Popup exist so a list of fifty is one query; these
    are the real numbers, and the two can disagree if events are pruned out
    from under the counters. That is deliberate -- a lifetime counter should
    not fall when old events age out.
    """

    @staticmethod
    def get_popup_analytics(popup, days=30):
        from apps.forms.models import FormSubmission
        from apps.tracking.models import TrackedEvent

        since = timezone.now() - timedelta(days=days)
        events = TrackedEvent.objects.filter(popup=popup, occurred_at__gte=since)

        totals = events.aggregate(
            impressions=Count('id', filter=Q(event_type=TrackedEvent.EVENT_POPUP_SHOWN)),
            unique_views=Count(
                'visitor', distinct=True,
                filter=Q(event_type=TrackedEvent.EVENT_POPUP_SHOWN),
            ),
            clicks=Count('id', filter=Q(event_type=TrackedEvent.EVENT_POPUP_CLICKED)),
            dismissals=Count(
                'id', filter=Q(event_type=TrackedEvent.EVENT_POPUP_DISMISSED)),
        )

        # A conversion is the submission row, not a fourth event type.
        conversions = 0
        if popup.form_id:
            conversions = FormSubmission.objects.filter(
                form_id=popup.form_id, created_at__gte=since,
            ).count()
        else:
            conversions = totals['clicks']

        impressions = totals['impressions'] or 0
        return {
            'impressions': impressions,
            'unique_views': totals['unique_views'] or 0,
            'clicks': totals['clicks'] or 0,
            'dismissals': totals['dismissals'] or 0,
            'conversions': conversions,
            'conversion_rate': (
                round(conversions / impressions * 100, 2) if impressions else 0.0
            ),
            'dismiss_rate': (
                round((totals['dismissals'] or 0) / impressions * 100, 2)
                if impressions else 0.0
            ),
            'over_time': PopupAnalyticsService._over_time(events, since, days),
        }

    @staticmethod
    def _over_time(events, since, days):
        from apps.tracking.models import TrackedEvent

        rows = (
            events
            .annotate(date=TruncDate('occurred_at'))
            .values('date')
            .annotate(
                impressions=Count(
                    'id', filter=Q(event_type=TrackedEvent.EVENT_POPUP_SHOWN)),
                clicks=Count(
                    'id', filter=Q(event_type=TrackedEvent.EVENT_POPUP_CLICKED)),
            )
            .order_by('date')
        )
        by_date = {row['date']: row for row in rows}

        out = []
        for offset in range(days):
            day = (since + timedelta(days=offset)).date()
            row = by_date.get(day)
            out.append({
                'date': day.isoformat(),
                'impressions': row['impressions'] if row else 0,
                'clicks': row['clicks'] if row else 0,
            })
        return out
