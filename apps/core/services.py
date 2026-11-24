"""
The dashboard: what needs you, what is yours, what is coming, and whether the
machine is working.

It is deliberately not a smaller Analytics. Anything retrospective -- top
pages, per-day breakdowns, exports -- lives there; what stays here is what asks
for a decision today. Every block is filtered by the viewer's own permission,
because one response carrying six modules' data is exactly where an
aggregating endpoint leaks.
"""
from datetime import timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.core import access
from apps.core.alerts import alerts_for

# A task assigned within this window is still worth marking as new.
NEW_TASK_HOURS = 24


class DashboardService:
    """Service class for dashboard statistics."""

    @staticmethod
    def get_contact_growth(organization, days=30):
        """
        Get contact growth data over time.

        Args:
            organization: The organization
            days: Number of days to look back (default 30)

        Returns:
            List of daily contact counts
        """
        from apps.contacts.models import Contact

        start_date = timezone.now() - timedelta(days=days)

        # Get contacts created per day
        growth_data = (
            Contact.objects
            .filter(
                organization=organization,
                deleted_at__isnull=True,
                created_at__gte=start_date
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        return [
            {
                'date': item['date'].isoformat(),
                'count': item['count']
            }
            for item in growth_data
        ]

    @staticmethod
    def get_campaign_stats(organization, days=30):
        """
        Get campaign statistics.

        Args:
            organization: The organization
            days: Number of days to look back

        Returns:
            Campaign performance metrics
        """
        from apps.campaigns.models import Campaign, CampaignRecipient

        start_date = timezone.now() - timedelta(days=days)

        # Get sent campaigns in the period
        sent_campaigns = Campaign.objects.filter(
            organization=organization,
            deleted_at__isnull=True,
            status='sent',
            sent_at__gte=start_date
        )

        campaign_ids = sent_campaigns.values_list('id', flat=True)

        # Calculate aggregate stats from recipients
        recipient_stats = CampaignRecipient.objects.filter(
            campaign_id__in=campaign_ids
        ).aggregate(
            total_sent=Count('id'),
            # Shared definition — see CampaignRecipient.delivered_filter().
            # This previously asked for status='delivered' alone, which drops
            # anyone who went on to open or click, so the dashboard reported
            # fewer delivered than the campaign report for the same send.
            total_delivered=Count('id', filter=CampaignRecipient.delivered_filter()),
            total_opened=Count('id', filter=Q(opened_at__isnull=False)),
            total_clicked=Count('id', filter=Q(clicked_at__isnull=False)),
            total_bounced=Count('id', filter=CampaignRecipient.bounced_filter()),
        )

        total_sent = recipient_stats['total_sent'] or 0
        total_delivered = recipient_stats['total_delivered'] or 0
        total_opened = recipient_stats['total_opened'] or 0
        total_clicked = recipient_stats['total_clicked'] or 0

        # Calculate rates
        open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
        click_rate = (total_clicked / total_delivered * 100) if total_delivered > 0 else 0

        total_bounced = recipient_stats['total_bounced'] or 0
        delivered_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0

        return {
            'campaigns_sent': sent_campaigns.count(),
            'emails_sent': total_sent,
            'emails_delivered': total_delivered,
            'emails_opened': total_opened,
            'emails_clicked': total_clicked,
            'emails_bounced': total_bounced,
            'open_rate': round(open_rate, 1),
            'click_rate': round(click_rate, 1),
            'delivered_rate': round(delivered_rate, 1),
            'bounce_rate': round(bounce_rate, 2),
        }

    @staticmethod
    def get_form_stats(organization, days=30):
        """
        Get form submission statistics.

        Args:
            organization: The organization
            days: Number of days to look back

        Returns:
            Form submission metrics
        """
        from apps.forms.models import Form, FormSubmission

        start_date = timezone.now() - timedelta(days=days)

        # Get all org forms
        form_ids = Form.objects.filter(
            organization=organization,
            deleted_at__isnull=True
        ).values_list('id', flat=True)

        # Total submissions in period
        total_submissions = FormSubmission.objects.filter(
            form_id__in=form_ids,
            created_at__gte=start_date
        ).count()

        # Submissions by day
        submissions_by_day = (
            FormSubmission.objects
            .filter(
                form_id__in=form_ids,
                created_at__gte=start_date
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        return {
            'total_submissions': total_submissions,
            'submissions_by_day': [
                {
                    'date': item['date'].isoformat(),
                    'count': item['count']
                }
                for item in submissions_by_day
            ]
        }

    @staticmethod
    def get_landing_page_stats(organization, days=30):
        """
        Get landing page view statistics.

        Args:
            organization: The organization
            days: Number of days to look back

        Returns:
            Landing page view metrics
        """
        from apps.landing_pages.models import LandingPage, PageView

        start_date = timezone.now() - timedelta(days=days)

        # Get all org landing pages
        page_ids = LandingPage.objects.filter(
            organization=organization,
            deleted_at__isnull=True
        ).values_list('id', flat=True)

        # Total views in period
        view_stats = PageView.objects.filter(
            landing_page_id__in=page_ids,
            created_at__gte=start_date
        ).aggregate(
            total_views=Count('id'),
            unique_views=Count('id', filter=Q(is_unique=True))
        )

        # Views by day
        views_by_day = (
            PageView.objects
            .filter(
                landing_page_id__in=page_ids,
                created_at__gte=start_date
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                views=Count('id'),
                unique_views=Count('id', filter=Q(is_unique=True))
            )
            .order_by('date')
        )

        return {
            'total_views': view_stats['total_views'] or 0,
            'unique_views': view_stats['unique_views'] or 0,
            'views_by_day': [
                {
                    'date': item['date'].isoformat(),
                    'views': item['views'],
                    'unique_views': item['unique_views']
                }
                for item in views_by_day
            ]
        }

    @staticmethod
    def get_recent_campaigns(organization, limit=5):
        """
        Get recent campaigns.

        Args:
            organization: The organization
            limit: Number of campaigns to return

        Returns:
            List of recent campaigns
        """
        from apps.campaigns.models import Campaign

        campaigns = Campaign.objects.filter(
            organization=organization,
            deleted_at__isnull=True
        ).order_by('-created_at')[:limit]

        return [
            {
                'id': str(campaign.id),
                'name': campaign.name,
                'status': campaign.status,
                'created_at': campaign.created_at.isoformat(),
                'sent_at': campaign.sent_at.isoformat() if campaign.sent_at else None,
            }
            for campaign in campaigns
        ]

    @staticmethod
    def get_recent_form_submissions(organization, limit=5):
        """
        Get recent form submissions.

        Args:
            organization: The organization
            limit: Number of submissions to return

        Returns:
            List of recent submissions
        """
        from apps.forms.models import Form, FormSubmission

        form_ids = Form.objects.filter(
            organization=organization,
            deleted_at__isnull=True
        ).values_list('id', flat=True)

        submissions = FormSubmission.objects.filter(
            form_id__in=form_ids
        ).select_related('form', 'contact').order_by('-created_at')[:limit]

        return [
            {
                'id': str(sub.id),
                'form_name': sub.form.name,
                'contact_email': sub.contact.email if sub.contact else None,
                'created_at': sub.created_at.isoformat(),
            }
            for sub in submissions
        ]

    @staticmethod
    def get_assigned_to_me(user, limit=4):
        """
        The tasks and calls this person has been given, soonest first.

        Overdue before today before later, because that is the order someone
        works through them. `is_new` comes from created_at: there is no
        assigned_at column, so a task reassigned later does not read as new.
        shortcut: new-ness is creation time, upgrade when CRMTask gains
        assigned_at.
        """
        from apps.crm.models import Activity, CRMTask

        organization = user.organization
        now = timezone.now()
        today = now.date()
        fresh_after = now - timedelta(hours=NEW_TASK_HOURS)

        items = []

        tasks = CRMTask.objects.filter(
            organization=organization, assigned_to=user,
        ).exclude(status='done').select_related('deal').order_by('due_date')[:20]

        for task in tasks:
            due = task.due_date
            items.append({
                'id': f'task:{task.id}',
                'title': task.title,
                'due': due.isoformat() if due else None,
                'overdue': bool(due and due < today),
                'today': bool(due and due == today),
                'is_new': task.created_at >= fresh_after,
                'meta': task.deal.title if task.deal_id else '',
                'url': f'/crm/deals/{task.deal_id}' if task.deal_id else '/crm',
            })

        activities = Activity.objects.filter(
            organization=organization, assigned_to=user, is_completed=False,
            due_date__isnull=False,
        ).select_related('deal').order_by('due_date')[:20]

        for activity in activities:
            due = activity.due_date
            items.append({
                'id': f'activity:{activity.id}',
                'title': activity.title,
                'due': due.isoformat(),
                'overdue': due < now,
                'today': due.date() == today,
                'is_new': activity.created_at >= fresh_after,
                'meta': activity.deal.title if activity.deal_id else activity.activity_type,
                'url': f'/crm/deals/{activity.deal_id}' if activity.deal_id else '/crm',
            })

        # Undated work sorts last rather than first, which is what an empty
        # due date would otherwise do.
        items.sort(key=lambda i: (not i['overdue'], not i['today'], i['due'] or '9999'))

        return {
            'items': items[:limit],
            'new_count': sum(1 for i in items if i['is_new']),
            'more': max(0, len(items) - limit),
        }

    @staticmethod
    def get_net_audience(organization, days=30):
        """Contacts gained minus contacts lost. The growth figure that can fall."""
        from apps.contacts.models import Contact

        since = timezone.now() - timedelta(days=days)
        added = Contact.objects.filter(
            organization=organization, deleted_at__isnull=True, created_at__gte=since
        ).count()
        unsubscribed = Contact.objects.filter(
            organization=organization, deleted_at__isnull=True,
            unsubscribed_at__gte=since,
        ).count()
        return {'added': added, 'unsubscribed': unsubscribed, 'net': added - unsubscribed}

    @staticmethod
    def get_conversion(organization, days=30):
        """Form submissions against landing page views, as a percentage."""
        forms = DashboardService.get_form_stats(organization, days)
        pages = DashboardService.get_landing_page_stats(organization, days)
        submissions = forms['total_submissions']
        views = pages['total_views']
        rate = (submissions / views * 100) if views else 0
        return {
            'submissions': submissions,
            'views': views,
            'rate': round(rate, 1),
            'by_day': [d['count'] for d in forms['submissions_by_day']],
        }

    @staticmethod
    def _delta(current, previous):
        """The change between two periods, or None when there is nothing to compare."""
        if previous in (None, 0):
            return None
        return round(current - previous, 1)

    @staticmethod
    def get_tiles(user, days=30):
        """
        Four rates, each with the previous period to compare against.

        Rates, never totals: a running total only ever goes up, so it cannot
        prompt anything. Each tile is omitted for a viewer who may not see the
        module it reads.
        """
        organization = user.organization
        tiles = []

        if access.has_permission(user, 'campaigns.view'):
            now = DashboardService.get_campaign_stats(organization, days)
            before = DashboardService.get_campaign_stats(organization, days * 2)
            # The earlier window is the outer period minus the inner one.
            previous_sent = before['emails_sent'] - now['emails_sent']
            previous_delivered = before['emails_delivered'] - now['emails_delivered']
            previous_opened = before['emails_opened'] - now['emails_opened']
            previous_delivered_rate = (
                previous_delivered / previous_sent * 100 if previous_sent else None
            )
            previous_open_rate = (
                previous_opened / previous_delivered * 100 if previous_delivered else None
            )

            tiles.append({
                'key': 'deliverability',
                'label': 'Deliverability',
                'value': now['delivered_rate'],
                'unit': '%',
                'delta': DashboardService._delta(
                    now['delivered_rate'], previous_delivered_rate
                ),
                'delta_unit': 'pts',
                'sub': f"Bounce {now['bounce_rate']}% · {now['emails_sent']:,} sent",
            })
            tiles.append({
                'key': 'engagement',
                'label': 'Engagement',
                'value': now['open_rate'],
                'unit': '%',
                'delta': DashboardService._delta(now['open_rate'], previous_open_rate),
                'delta_unit': 'pts',
                'sub': f"{now['click_rate']}% clicked · {now['emails_opened']:,} opens",
            })

        if access.has_permission(user, 'contacts.view'):
            now = DashboardService.get_net_audience(organization, days)
            before = DashboardService.get_net_audience(organization, days * 2)
            previous_net = before['net'] - now['net']
            growth = DashboardService.get_contact_growth(organization, days)
            tiles.append({
                'key': 'audience',
                'label': 'Net audience',
                'value': now['net'],
                'unit': '',
                'delta': DashboardService._delta(now['net'], previous_net),
                'delta_unit': '',
                'sub': f"{now['added']:,} added · {now['unsubscribed']:,} unsubscribed",
                'spark': [d['count'] for d in growth],
            })

        if access.has_permission(user, 'forms.view'):
            now = DashboardService.get_conversion(organization, days)
            before = DashboardService.get_conversion(organization, days * 2)
            tiles.append({
                'key': 'conversion',
                'label': 'Conversion',
                'value': now['rate'],
                'unit': '%',
                'delta': DashboardService._delta(now['rate'], before['rate'] or None),
                'delta_unit': 'pts',
                'sub': f"{now['submissions']:,} submissions from {now['views']:,} visits",
                'spark': now['by_day'],
            })

        return tiles

    @staticmethod
    def get_upcoming(user):
        """
        The next seven days, as the calendar already assembles them.

        Reused rather than rebuilt: the calendar service filters each source by
        the viewer's permission, so this inherits that for free.
        """
        from apps.core.calendar import CalendarService, resolve_range, viewer_timezone

        tzinfo = viewer_timezone(user)
        first = timezone.now().astimezone(tzinfo).date()
        last = first + timedelta(days=6)
        start, end, start_date, end_date = resolve_range(user, first, last)

        payload = CalendarService(user, start, end, start_date, end_date).payload()
        if not payload['sources']:
            return None

        buckets = {}
        for event in payload['events']:
            buckets.setdefault(event['start'][:10], []).append({
                'kind': event['source'],
                'label': event['title'],
                'all_day': event['all_day'],
                'time': None if event['all_day'] else event['start'][11:16],
            })

        days = []
        for offset in range(7):
            day = first + timedelta(days=offset)
            key = day.isoformat()
            days.append({'date': key, 'items': buckets.get(key, [])[:3]})

        return {
            'days': days,
            'total': len(payload['events']),
            'sources': payload['sources'],
        }

    @staticmethod
    def get_dashboard_data(user, days=30):
        """
        Everything the dashboard shows, with each block left out entirely when
        the viewer's role does not reach its data.
        """
        organization = user.organization

        data = {
            'days': days,
            'alerts': alerts_for(user),
            'tiles': DashboardService.get_tiles(user, days),
            'upcoming': DashboardService.get_upcoming(user),
        }

        if access.has_permission(user, 'crm.view'):
            data['assigned'] = DashboardService.get_assigned_to_me(user)

        if access.has_permission(user, 'campaigns.view'):
            data['recent_campaigns'] = DashboardService.get_recent_campaigns(organization)

        if access.has_permission(user, 'forms.view'):
            data['recent_submissions'] = DashboardService.get_recent_form_submissions(
                organization
            )

        return data
