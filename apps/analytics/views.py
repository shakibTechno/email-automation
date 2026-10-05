"""
Views for the Analytics app - read-only aggregation endpoints.
"""
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOrganizationMember
from apps.campaigns.models import Campaign

from .services import (
    AnalyticsOverviewService,
    CampaignAnalyticsService,
    ContactAnalyticsService,
    FormAnalyticsService,
    LandingPageAnalyticsService,
)


def _get_days(request):
    """Extract and clamp days parameter."""
    days = int(request.query_params.get('days', 30))
    return max(7, min(days, 365))


class AnalyticsOverviewView(APIView):
    """Aggregated overview stats with trends."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        org = request.user.organization
        days = _get_days(request)

        return Response({
            'overview': AnalyticsOverviewService.get_overview(org, days),
            'trends': AnalyticsOverviewService.get_trends(org, days),
        })


class CampaignAnalyticsListView(APIView):
    """Campaign metrics table with summary."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        org = request.user.organization
        days = _get_days(request)

        data = CampaignAnalyticsService.get_campaigns_with_metrics(org, days)
        data['top_campaigns'] = CampaignAnalyticsService.get_top_campaigns(org, days)
        return Response(data)


class CampaignAnalyticsDetailView(APIView):
    """Single campaign detail analytics."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request, campaign_id):
        org = request.user.organization

        try:
            campaign = Campaign.objects.get(
                id=campaign_id,
                organization=org,
                deleted_at__isnull=True,
            )
        except Campaign.DoesNotExist:
            return Response({'detail': 'Campaign not found.'}, status=404)

        data = CampaignAnalyticsService.get_campaign_detail(campaign)
        return Response(data)


class CampaignComparisonView(APIView):
    """Compare multiple campaigns side by side."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        org = request.user.organization
        ids_param = request.query_params.get('ids', '')

        if not ids_param:
            return Response({'detail': 'Provide campaign ids via ?ids=uuid1,uuid2'}, status=400)

        campaign_ids = [i.strip() for i in ids_param.split(',') if i.strip()]

        campaigns = Campaign.objects.filter(
            id__in=campaign_ids,
            organization=org,
            deleted_at__isnull=True,
        )

        if not campaigns.exists():
            return Response({'detail': 'No campaigns found.'}, status=404)

        data = CampaignAnalyticsService.compare_campaigns(campaigns)
        return Response(data)


class CampaignExportView(APIView):
    """Export campaign recipient data as CSV."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request, campaign_id):
        org = request.user.organization

        try:
            campaign = Campaign.objects.get(
                id=campaign_id,
                organization=org,
                deleted_at__isnull=True,
            )
        except Campaign.DoesNotExist:
            return Response({'detail': 'Campaign not found.'}, status=404)

        csv_content = CampaignAnalyticsService.export_campaign_csv(campaign)

        response = HttpResponse(csv_content, content_type='text/csv')
        filename = f"campaign_{campaign.name.replace(' ', '_')}_{campaign_id}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ContactAnalyticsView(APIView):
    """Contact growth, engagement, and source analytics."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        org = request.user.organization
        days = _get_days(request)

        data = ContactAnalyticsService.get_contact_analytics(org, days)
        return Response(data)


class FormAnalyticsView(APIView):
    """Form submission analytics."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        org = request.user.organization
        days = _get_days(request)

        data = FormAnalyticsService.get_form_analytics(org, days)
        return Response(data)


class LandingPageAnalyticsView(APIView):
    """Landing page view, referrer, and device analytics."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        org = request.user.organization
        days = _get_days(request)

        data = LandingPageAnalyticsService.get_landing_page_analytics(org, days)
        return Response(data)
