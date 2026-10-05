"""
Core views for the application.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from .permissions import IsOrganizationMember
from .services import DashboardService

logger = logging.getLogger(__name__)


class DashboardView(APIView):
    """Dashboard API view for fetching all dashboard statistics."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        """
        Get dashboard data.

        Query params:
            days: Number of days to look back (default 30)
        """
        organization = request.user.organization
        days = int(request.query_params.get('days', 30))

        # Clamp days to reasonable range
        days = max(7, min(days, 365))

        data = DashboardService.get_dashboard_data(organization, days)
        return Response(data)


class DashboardOverviewView(APIView):
    """Dashboard overview statistics."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        """Get overview statistics."""
        organization = request.user.organization
        data = DashboardService.get_overview_stats(organization)
        return Response(data)


class DashboardCampaignStatsView(APIView):
    """Dashboard campaign statistics."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        """Get campaign statistics."""
        organization = request.user.organization
        days = int(request.query_params.get('days', 30))
        data = DashboardService.get_campaign_stats(organization, days)
        return Response(data)


class DashboardContactGrowthView(APIView):
    """Dashboard contact growth chart data."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        """Get contact growth data."""
        organization = request.user.organization
        days = int(request.query_params.get('days', 30))
        data = DashboardService.get_contact_growth(organization, days)
        return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for load balancers and monitoring.
    Returns the health status of the application and its dependencies.
    """
    health_status = {
        'status': 'healthy',
        'database': 'unknown',
        'cache': 'unknown',
    }

    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            health_status['database'] = 'healthy'
    except Exception as e:
        health_status['database'] = 'unhealthy'
        health_status['status'] = 'unhealthy'
        logger.error(f"Database health check failed: {str(e)}")

    # Check cache connection
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['cache'] = 'healthy'
        else:
            health_status['cache'] = 'unhealthy'
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['cache'] = 'unhealthy'
        health_status['status'] = 'degraded'
        logger.error(f"Cache health check failed: {str(e)}")

    status_code = 200 if health_status['status'] != 'unhealthy' else 503
    return JsonResponse(health_status, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Readiness check endpoint for Kubernetes readiness probes.
    """
    return JsonResponse({'status': 'ready'}, status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Liveness check endpoint for Kubernetes liveness probes.
    """
    return JsonResponse({'status': 'alive'}, status=200)
