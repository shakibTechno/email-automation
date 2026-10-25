"""
Services for the Core app - Dashboard statistics.
"""
from datetime import timedelta
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone


class DashboardService:
    """Service class for dashboard statistics."""

    @staticmethod
    def get_overview_stats(organization):
        """
        Get overview statistics for the dashboard.

        Returns counts for:
        - Total contacts
        - Total campaigns
        - Total forms
        - Total landing pages
        """
        from apps.contacts.models import Contact
        from apps.campaigns.models import Campaign
        from apps.forms.models import Form
        from apps.landing_pages.models import LandingPage

        # Get counts
        total_contacts = Contact.objects.filter(
            organization=organization,
            deleted_at__isnull=True
        ).count()

        total_campaigns = Campaign.objects.filter(
            organization=organization,
            deleted_at__isnull=True
        ).count()

        sent_campaigns = Campaign.objects.filter(
            organization=organization,
            deleted_at__isnull=True,
            status='sent'
        ).count()

        total_forms = Form.objects.filter(
            organization=organization,
            deleted_at__isnull=True
        ).count()

        active_forms = Form.objects.filter(
            organization=organization,
            deleted_at__isnull=True,
            status='active'
        ).count()

        total_landing_pages = LandingPage.objects.filter(
            organization=organization,
            deleted_at__isnull=True
        ).count()

        published_landing_pages = LandingPage.objects.filter(
            organization=organization,
            deleted_at__isnull=True,
            status='published'
        ).count()

        return {
            'contacts': {
                'total': total_contacts,
            },
            'campaigns': {
                'total': total_campaigns,
                'sent': sent_campaigns,
            },
            'forms': {
                'total': total_forms,
                'active': active_forms,
            },
            'landing_pages': {
                'total': total_landing_pages,
                'published': published_landing_pages,
            },
        }

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

        return {
            'campaigns_sent': sent_campaigns.count(),
            'emails_sent': total_sent,
            'emails_delivered': total_delivered,
            'emails_opened': total_opened,
            'emails_clicked': total_clicked,
            'open_rate': round(open_rate, 1),
            'click_rate': round(click_rate, 1),
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
    def get_top_performing_landing_pages(organization, limit=5):
        """
        Get top performing landing pages by views.

        Args:
            organization: The organization
            limit: Number of pages to return

        Returns:
            List of top pages
        """
        from apps.landing_pages.models import LandingPage

        pages = LandingPage.objects.filter(
            organization=organization,
            deleted_at__isnull=True,
            status='published'
        ).order_by('-view_count')[:limit]

        return [
            {
                'id': str(page.id),
                'name': page.name,
                'slug': page.slug,
                'view_count': page.view_count,
                'conversion_count': page.conversion_count,
            }
            for page in pages
        ]

    @staticmethod
    def get_dashboard_data(organization, days=30):
        """
        Get all dashboard data.

        Args:
            organization: The organization
            days: Number of days to look back

        Returns:
            Complete dashboard data
        """
        return {
            'overview': DashboardService.get_overview_stats(organization),
            'contact_growth': DashboardService.get_contact_growth(organization, days),
            'campaign_stats': DashboardService.get_campaign_stats(organization, days),
            'form_stats': DashboardService.get_form_stats(organization, days),
            'landing_page_stats': DashboardService.get_landing_page_stats(organization, days),
            'recent_campaigns': DashboardService.get_recent_campaigns(organization),
            'recent_submissions': DashboardService.get_recent_form_submissions(organization),
            'top_landing_pages': DashboardService.get_top_performing_landing_pages(organization),
        }
