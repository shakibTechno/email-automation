"""
Services for the Analytics app - read-only aggregation on existing data.
"""
import csv
import io
from datetime import timedelta
from urllib.parse import urlparse

from django.db.models import Count, Q, Avg, F
from django.db.models.functions import TruncDate
from django.utils import timezone


def _compare_periods(current_value, previous_value):
    """
    Compare current vs previous period values.

    Returns:
        dict with value, change_percent, and direction (up/down/flat)
    """
    if previous_value and previous_value > 0:
        change = ((current_value - previous_value) / previous_value) * 100
    elif current_value > 0:
        change = 100.0
    else:
        change = 0.0

    if change > 0:
        direction = 'up'
    elif change < 0:
        direction = 'down'
    else:
        direction = 'flat'

    return {
        'value': current_value,
        'change_percent': round(abs(change), 1),
        'direction': direction,
    }


class AnalyticsOverviewService:
    """Aggregated overview stats with period comparison."""

    @staticmethod
    def get_overview(organization, days=30):
        from apps.campaigns.models import Campaign, CampaignRecipient
        from apps.contacts.models import Contact
        from apps.forms.models import Form, FormSubmission
        from apps.landing_pages.models import LandingPage, PageView

        now = timezone.now()
        current_start = now - timedelta(days=days)
        previous_start = current_start - timedelta(days=days)

        # --- Emails sent ---
        org_campaigns = Campaign.objects.filter(
            organization=organization, deleted_at__isnull=True, status='sent'
        )
        current_campaign_ids = org_campaigns.filter(
            sent_at__gte=current_start
        ).values_list('id', flat=True)
        previous_campaign_ids = org_campaigns.filter(
            sent_at__gte=previous_start, sent_at__lt=current_start
        ).values_list('id', flat=True)

        current_emails = CampaignRecipient.objects.filter(
            campaign_id__in=current_campaign_ids
        ).count()
        previous_emails = CampaignRecipient.objects.filter(
            campaign_id__in=previous_campaign_ids
        ).count()

        # --- New contacts ---
        contact_qs = Contact.objects.filter(
            organization=organization, deleted_at__isnull=True
        )
        current_contacts = contact_qs.filter(created_at__gte=current_start).count()
        previous_contacts = contact_qs.filter(
            created_at__gte=previous_start, created_at__lt=current_start
        ).count()

        # --- Form submissions ---
        form_ids = Form.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)
        current_subs = FormSubmission.objects.filter(
            form_id__in=form_ids, created_at__gte=current_start
        ).count()
        previous_subs = FormSubmission.objects.filter(
            form_id__in=form_ids,
            created_at__gte=previous_start,
            created_at__lt=current_start,
        ).count()

        # --- Page views ---
        page_ids = LandingPage.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)
        current_views = PageView.objects.filter(
            landing_page_id__in=page_ids, created_at__gte=current_start
        ).count()
        previous_views = PageView.objects.filter(
            landing_page_id__in=page_ids,
            created_at__gte=previous_start,
            created_at__lt=current_start,
        ).count()

        return {
            'emails_sent': _compare_periods(current_emails, previous_emails),
            'new_contacts': _compare_periods(current_contacts, previous_contacts),
            'form_submissions': _compare_periods(current_subs, previous_subs),
            'page_views': _compare_periods(current_views, previous_views),
        }

    @staticmethod
    def get_trends(organization, days=30):
        from apps.campaigns.models import Campaign, CampaignRecipient
        from apps.contacts.models import Contact
        from apps.forms.models import Form, FormSubmission
        from apps.landing_pages.models import LandingPage, PageView

        start_date = timezone.now() - timedelta(days=days)

        # Emails sent per day
        sent_campaign_ids = Campaign.objects.filter(
            organization=organization, deleted_at__isnull=True,
            status='sent', sent_at__gte=start_date
        ).values_list('id', flat=True)

        emails_by_day = dict(
            CampaignRecipient.objects.filter(
                campaign_id__in=sent_campaign_ids,
                sent_at__gte=start_date
            ).annotate(date=TruncDate('sent_at'))
            .values('date')
            .annotate(count=Count('id'))
            .values_list('date', 'count')
        )

        # Contacts per day
        contacts_by_day = dict(
            Contact.objects.filter(
                organization=organization, deleted_at__isnull=True,
                created_at__gte=start_date
            ).annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .values_list('date', 'count')
        )

        # Submissions per day
        form_ids = Form.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)
        subs_by_day = dict(
            FormSubmission.objects.filter(
                form_id__in=form_ids, created_at__gte=start_date
            ).annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .values_list('date', 'count')
        )

        # Page views per day
        page_ids = LandingPage.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)
        views_by_day = dict(
            PageView.objects.filter(
                landing_page_id__in=page_ids, created_at__gte=start_date
            ).annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .values_list('date', 'count')
        )

        # Build unified timeline
        all_dates = sorted(set(
            list(emails_by_day.keys()) +
            list(contacts_by_day.keys()) +
            list(subs_by_day.keys()) +
            list(views_by_day.keys())
        ))

        trends = []
        for d in all_dates:
            trends.append({
                'date': d.isoformat(),
                'emails_sent': emails_by_day.get(d, 0),
                'new_contacts': contacts_by_day.get(d, 0),
                'form_submissions': subs_by_day.get(d, 0),
                'page_views': views_by_day.get(d, 0),
            })

        return trends


class CampaignAnalyticsService:
    """Per-campaign metrics, comparison, and export."""

    @staticmethod
    def get_campaigns_with_metrics(organization, days=30):
        from apps.campaigns.models import Campaign, CampaignRecipient

        start_date = timezone.now() - timedelta(days=days)

        campaigns = Campaign.objects.filter(
            organization=organization,
            deleted_at__isnull=True,
            status='sent',
            sent_at__gte=start_date,
        ).order_by('-sent_at')

        result = []
        for c in campaigns:
            recipients = CampaignRecipient.objects.filter(campaign=c)
            total = recipients.count()
            delivered = recipients.filter(
                Q(status='delivered') | Q(status='opened') | Q(status='clicked')
            ).count()
            opened = recipients.filter(opened_at__isnull=False).count()
            clicked = recipients.filter(clicked_at__isnull=False).count()
            bounced = recipients.filter(status='bounced').count()

            open_rate = round((opened / delivered * 100), 1) if delivered > 0 else 0
            click_rate = round((clicked / delivered * 100), 1) if delivered > 0 else 0
            bounce_rate = round((bounced / total * 100), 1) if total > 0 else 0

            result.append({
                'id': str(c.id),
                'name': c.name,
                'subject': c.subject,
                'sent_at': c.sent_at.isoformat() if c.sent_at else None,
                'recipient_count': total,
                'delivered': delivered,
                'opened': opened,
                'clicked': clicked,
                'bounced': bounced,
                'open_rate': open_rate,
                'click_rate': click_rate,
                'bounce_rate': bounce_rate,
            })

        # Summary stats
        total_sent = sum(c['recipient_count'] for c in result)
        avg_open = round(sum(c['open_rate'] for c in result) / len(result), 1) if result else 0
        avg_click = round(sum(c['click_rate'] for c in result) / len(result), 1) if result else 0
        total_bounced = sum(c['bounced'] for c in result)

        return {
            'summary': {
                'total_sent': total_sent,
                'avg_open_rate': avg_open,
                'avg_click_rate': avg_click,
                'total_bounced': total_bounced,
                'campaign_count': len(result),
            },
            'campaigns': result,
        }

    @staticmethod
    def get_campaign_detail(campaign):
        from apps.campaigns.models import CampaignRecipient

        recipients = CampaignRecipient.objects.filter(campaign=campaign)
        total = recipients.count()

        # Status breakdown for pie chart
        statuses = recipients.values('status').annotate(count=Count('id'))
        status_breakdown = [
            {'status': s['status'], 'count': s['count']}
            for s in statuses
        ]

        # Engagement timeline: opens and clicks per day
        opens_by_day = dict(
            recipients.filter(opened_at__isnull=False)
            .annotate(date=TruncDate('opened_at'))
            .values('date')
            .annotate(count=Count('id'))
            .values_list('date', 'count')
        )
        clicks_by_day = dict(
            recipients.filter(clicked_at__isnull=False)
            .annotate(date=TruncDate('clicked_at'))
            .values('date')
            .annotate(count=Count('id'))
            .values_list('date', 'count')
        )

        all_dates = sorted(set(list(opens_by_day.keys()) + list(clicks_by_day.keys())))
        engagement_over_time = [
            {
                'date': d.isoformat(),
                'opens': opens_by_day.get(d, 0),
                'clicks': clicks_by_day.get(d, 0),
            }
            for d in all_dates
        ]

        delivered = recipients.filter(
            Q(status='delivered') | Q(status='opened') | Q(status='clicked')
        ).count()
        opened = recipients.filter(opened_at__isnull=False).count()
        clicked = recipients.filter(clicked_at__isnull=False).count()
        bounced = recipients.filter(status='bounced').count()

        return {
            'campaign': {
                'id': str(campaign.id),
                'name': campaign.name,
                'subject': campaign.subject,
                'sent_at': campaign.sent_at.isoformat() if campaign.sent_at else None,
            },
            'recipient_count': total,
            'delivered': delivered,
            'opened': opened,
            'clicked': clicked,
            'bounced': bounced,
            'open_rate': round((opened / delivered * 100), 1) if delivered > 0 else 0,
            'click_rate': round((clicked / delivered * 100), 1) if delivered > 0 else 0,
            'bounce_rate': round((bounced / total * 100), 1) if total > 0 else 0,
            'status_breakdown': status_breakdown,
            'engagement_over_time': engagement_over_time,
        }

    @staticmethod
    def compare_campaigns(campaigns):
        results = []
        for campaign in campaigns:
            detail = CampaignAnalyticsService.get_campaign_detail(campaign)
            results.append(detail)
        return results

    @staticmethod
    def get_top_campaigns(organization, days=30, metric='open_rate', limit=5):
        data = CampaignAnalyticsService.get_campaigns_with_metrics(organization, days)
        campaigns = data['campaigns']
        sorted_campaigns = sorted(campaigns, key=lambda c: c.get(metric, 0), reverse=True)
        return sorted_campaigns[:limit]

    @staticmethod
    def export_campaign_csv(campaign):
        from apps.campaigns.models import CampaignRecipient

        recipients = CampaignRecipient.objects.filter(
            campaign=campaign
        ).select_related('contact').order_by('email')

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Email', 'Status', 'Sent At', 'Opened At', 'Clicked At', 'Bounced At'])

        for r in recipients:
            writer.writerow([
                r.email,
                r.status,
                r.sent_at.isoformat() if r.sent_at else '',
                r.opened_at.isoformat() if r.opened_at else '',
                r.clicked_at.isoformat() if r.clicked_at else '',
                r.bounced_at.isoformat() if r.bounced_at else '',
            ])

        return output.getvalue()


class ContactAnalyticsService:
    """Contact growth, engagement, and source analytics."""

    @staticmethod
    def get_growth(organization, days=30):
        from apps.contacts.models import Contact

        start_date = timezone.now() - timedelta(days=days)

        growth_data = (
            Contact.objects.filter(
                organization=organization,
                deleted_at__isnull=True,
                created_at__gte=start_date,
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        return [
            {'date': item['date'].isoformat(), 'count': item['count']}
            for item in growth_data
        ]

    @staticmethod
    def get_engagement_distribution(organization):
        from apps.contacts.models import Contact

        dist = (
            Contact.objects.filter(
                organization=organization, deleted_at__isnull=True
            )
            .values('engagement_level')
            .annotate(count=Count('id'))
            .order_by('engagement_level')
        )

        return [
            {'level': item['engagement_level'], 'count': item['count']}
            for item in dist
        ]

    @staticmethod
    def get_source_distribution(organization):
        from apps.contacts.models import Contact

        dist = (
            Contact.objects.filter(
                organization=organization, deleted_at__isnull=True
            )
            .values('source')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return [
            {'source': item['source'], 'count': item['count']}
            for item in dist
        ]

    @staticmethod
    def get_subscription_overview(organization):
        from apps.contacts.models import Contact

        qs = Contact.objects.filter(
            organization=organization, deleted_at__isnull=True
        )

        return {
            'subscribed': qs.filter(is_subscribed=True).count(),
            'unsubscribed': qs.filter(is_subscribed=False).count(),
            'bounced': qs.filter(bounced_at__isnull=False).count(),
        }

    @staticmethod
    def get_lead_score_distribution(organization):
        from apps.contacts.models import Contact

        qs = Contact.objects.filter(
            organization=organization, deleted_at__isnull=True
        )

        buckets = [
            ('0', Q(lead_score=0)),
            ('1-10', Q(lead_score__gte=1, lead_score__lte=10)),
            ('11-25', Q(lead_score__gte=11, lead_score__lte=25)),
            ('26-50', Q(lead_score__gte=26, lead_score__lte=50)),
            ('51-75', Q(lead_score__gte=51, lead_score__lte=75)),
            ('76-100', Q(lead_score__gte=76, lead_score__lte=100)),
            ('100+', Q(lead_score__gt=100)),
        ]

        result = []
        for label, q_filter in buckets:
            result.append({
                'bucket': label,
                'count': qs.filter(q_filter).count(),
            })

        return result

    @staticmethod
    def get_new_vs_unsubscribes(organization, days=30):
        from apps.contacts.models import Contact

        start_date = timezone.now() - timedelta(days=days)

        new_by_day = dict(
            Contact.objects.filter(
                organization=organization, deleted_at__isnull=True,
                created_at__gte=start_date,
            ).annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .values_list('date', 'count')
        )

        unsubs_by_day = dict(
            Contact.objects.filter(
                organization=organization, deleted_at__isnull=True,
                unsubscribed_at__isnull=False,
                unsubscribed_at__gte=start_date,
            ).annotate(date=TruncDate('unsubscribed_at'))
            .values('date')
            .annotate(count=Count('id'))
            .values_list('date', 'count')
        )

        all_dates = sorted(set(list(new_by_day.keys()) + list(unsubs_by_day.keys())))

        return [
            {
                'date': d.isoformat(),
                'new_contacts': new_by_day.get(d, 0),
                'unsubscribes': unsubs_by_day.get(d, 0),
            }
            for d in all_dates
        ]

    @staticmethod
    def get_contact_analytics(organization, days=30):
        from apps.contacts.models import Contact

        now = timezone.now()
        current_start = now - timedelta(days=days)
        previous_start = current_start - timedelta(days=days)

        qs = Contact.objects.filter(
            organization=organization, deleted_at__isnull=True
        )

        total = qs.count()
        current_new = qs.filter(created_at__gte=current_start).count()
        previous_new = qs.filter(
            created_at__gte=previous_start, created_at__lt=current_start
        ).count()

        current_unsubs = qs.filter(
            unsubscribed_at__isnull=False, unsubscribed_at__gte=current_start
        ).count()
        previous_unsubs = qs.filter(
            unsubscribed_at__isnull=False,
            unsubscribed_at__gte=previous_start,
            unsubscribed_at__lt=current_start,
        ).count()

        return {
            'total': total,
            'new_contacts': _compare_periods(current_new, previous_new),
            'unsubscribes': _compare_periods(current_unsubs, previous_unsubs),
            'growth': ContactAnalyticsService.get_growth(organization, days),
            'engagement_distribution': ContactAnalyticsService.get_engagement_distribution(organization),
            'source_distribution': ContactAnalyticsService.get_source_distribution(organization),
            'subscription_overview': ContactAnalyticsService.get_subscription_overview(organization),
            'lead_score_distribution': ContactAnalyticsService.get_lead_score_distribution(organization),
            'new_vs_unsubscribes': ContactAnalyticsService.get_new_vs_unsubscribes(organization, days),
        }


class FormAnalyticsService:
    """Form submission analytics."""

    @staticmethod
    def get_submissions_over_time(organization, days=30):
        from apps.forms.models import Form, FormSubmission

        start_date = timezone.now() - timedelta(days=days)
        form_ids = Form.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)

        data = (
            FormSubmission.objects.filter(
                form_id__in=form_ids, created_at__gte=start_date
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        return [
            {'date': item['date'].isoformat(), 'count': item['count']}
            for item in data
        ]

    @staticmethod
    def get_top_forms(organization, days=30, limit=10):
        from apps.forms.models import Form, FormSubmission

        start_date = timezone.now() - timedelta(days=days)
        form_ids = Form.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)

        top = (
            FormSubmission.objects.filter(
                form_id__in=form_ids, created_at__gte=start_date
            )
            .values('form_id', 'form__name')
            .annotate(submissions=Count('id'))
            .order_by('-submissions')[:limit]
        )

        return [
            {
                'id': str(item['form_id']),
                'name': item['form__name'],
                'submissions': item['submissions'],
            }
            for item in top
        ]

    @staticmethod
    def get_form_metrics(organization, days=30):
        from apps.forms.models import Form, FormSubmission

        start_date = timezone.now() - timedelta(days=days)
        forms = Form.objects.filter(
            organization=organization, deleted_at__isnull=True
        )

        result = []
        for form in forms:
            count = FormSubmission.objects.filter(
                form=form, created_at__gte=start_date
            ).count()
            result.append({
                'id': str(form.id),
                'name': form.name,
                'status': form.status,
                'submissions': count,
            })

        result.sort(key=lambda x: x['submissions'], reverse=True)
        return result

    @staticmethod
    def get_form_analytics(organization, days=30):
        return {
            'submissions_over_time': FormAnalyticsService.get_submissions_over_time(organization, days),
            'top_forms': FormAnalyticsService.get_top_forms(organization, days),
            'form_metrics': FormAnalyticsService.get_form_metrics(organization, days),
        }


class LandingPageAnalyticsService:
    """Landing page view, referrer, and device analytics."""

    @staticmethod
    def get_views_over_time(organization, days=30):
        from apps.landing_pages.models import LandingPage, PageView

        start_date = timezone.now() - timedelta(days=days)
        page_ids = LandingPage.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)

        data = (
            PageView.objects.filter(
                landing_page_id__in=page_ids, created_at__gte=start_date
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total=Count('id'),
                unique=Count('id', filter=Q(is_unique=True)),
            )
            .order_by('date')
        )

        return [
            {
                'date': item['date'].isoformat(),
                'total': item['total'],
                'unique': item['unique'],
            }
            for item in data
        ]

    @staticmethod
    def get_top_pages(organization, days=30, limit=10):
        from apps.landing_pages.models import LandingPage, PageView

        start_date = timezone.now() - timedelta(days=days)
        page_ids = LandingPage.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)

        top = (
            PageView.objects.filter(
                landing_page_id__in=page_ids, created_at__gte=start_date
            )
            .values('landing_page_id', 'landing_page__name')
            .annotate(views=Count('id'))
            .order_by('-views')[:limit]
        )

        return [
            {
                'id': str(item['landing_page_id']),
                'name': item['landing_page__name'],
                'views': item['views'],
            }
            for item in top
        ]

    @staticmethod
    def get_referrer_breakdown(organization, days=30):
        from apps.landing_pages.models import LandingPage, PageView

        start_date = timezone.now() - timedelta(days=days)
        page_ids = LandingPage.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)

        views = PageView.objects.filter(
            landing_page_id__in=page_ids,
            created_at__gte=start_date,
            referrer__gt='',
        ).values_list('referrer', flat=True)

        domain_counts = {}
        for ref in views:
            try:
                netloc = urlparse(ref).netloc
                if netloc:
                    domain_counts[netloc] = domain_counts.get(netloc, 0) + 1
            except Exception:
                continue

        direct_count = PageView.objects.filter(
            landing_page_id__in=page_ids,
            created_at__gte=start_date,
        ).filter(Q(referrer='') | Q(referrer__isnull=True)).count()

        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        result = [{'source': domain, 'count': count} for domain, count in sorted_domains]
        if direct_count > 0:
            result.insert(0, {'source': 'Direct', 'count': direct_count})

        return result

    @staticmethod
    def get_device_breakdown(organization, days=30):
        from apps.landing_pages.models import LandingPage, PageView

        start_date = timezone.now() - timedelta(days=days)
        page_ids = LandingPage.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)

        user_agents = PageView.objects.filter(
            landing_page_id__in=page_ids,
            created_at__gte=start_date,
        ).values_list('user_agent', flat=True)

        mobile_keywords = ['mobile', 'android', 'iphone', 'ipod', 'windows phone']
        tablet_keywords = ['tablet', 'ipad', 'kindle', 'silk']

        counts = {'Desktop': 0, 'Mobile': 0, 'Tablet': 0}
        for ua in user_agents:
            ua_lower = ua.lower()
            if any(kw in ua_lower for kw in tablet_keywords):
                counts['Tablet'] += 1
            elif any(kw in ua_lower for kw in mobile_keywords):
                counts['Mobile'] += 1
            else:
                counts['Desktop'] += 1

        return [
            {'device': device, 'count': count}
            for device, count in counts.items()
            if count > 0
        ]

    @staticmethod
    def get_landing_page_analytics(organization, days=30):
        from apps.landing_pages.models import LandingPage, PageView

        start_date = timezone.now() - timedelta(days=days)
        page_ids = LandingPage.objects.filter(
            organization=organization, deleted_at__isnull=True
        ).values_list('id', flat=True)

        stats = PageView.objects.filter(
            landing_page_id__in=page_ids, created_at__gte=start_date
        ).aggregate(
            total_views=Count('id'),
            unique_views=Count('id', filter=Q(is_unique=True)),
        )

        return {
            'total_views': stats['total_views'] or 0,
            'unique_views': stats['unique_views'] or 0,
            'views_over_time': LandingPageAnalyticsService.get_views_over_time(organization, days),
            'top_pages': LandingPageAnalyticsService.get_top_pages(organization, days),
            'referrer_breakdown': LandingPageAnalyticsService.get_referrer_breakdown(organization, days),
            'device_breakdown': LandingPageAnalyticsService.get_device_breakdown(organization, days),
        }
