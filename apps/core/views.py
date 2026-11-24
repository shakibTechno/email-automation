"""
Core views for the application.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from .calendar import MAX_RANGE_DAYS, CalendarService, resolve_range
from .permissions import IsOrganizationMember
from .services import DashboardService

logger = logging.getLogger(__name__)


class DashboardView(APIView):
    """
    GET /api/v1/dashboard/?days=30

    Deliberately NOT gated by HasResourcePermission: this module is
    `apps.core`, which the access registry maps to the `analytics` resource, so
    the class would ask for `analytics.view` and hand anyone who can read a
    chart the organization's billing state, its CRM work and its sending
    health. DashboardService filters every block by the viewer's own
    permission instead, and a viewer with none gets a page with nothing on it
    rather than a 403.
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
        except (TypeError, ValueError):
            days = 30
        # The comparison window is the same length again, so a long period
        # doubles the rows read. 90 days is what the UI offers.
        days = max(1, min(days, 90))

        return Response(DashboardService.get_dashboard_data(request.user, days))


class CalendarView(APIView):
    """
    GET /api/v1/calendar/?start=2026-11-01&end=2026-11-30

    Every dated thing in the range, in one shape.

    Deliberately NOT gated by HasResourcePermission: this module is `apps.core`,
    which the access registry maps to the `analytics` resource, so the class
    would ask for `analytics.view` and let anyone who can read a chart see every
    scheduled campaign and sales task. CalendarService filters each source by
    the viewer's own permission instead, which is the finer check -- a viewer
    with none gets an empty calendar rather than a 403.
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        start_date = self._date(request, 'start')
        end_date = self._date(request, 'end')
        if isinstance(start_date, Response):
            return start_date
        if isinstance(end_date, Response):
            return end_date

        start, end, start_date, end_date = resolve_range(
            request.user, start_date, end_date
        )
        if end_date < start_date:
            return Response(
                {'error': '`end` falls before `start`.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        span = (end_date - start_date).days + 1
        if span > MAX_RANGE_DAYS:
            return Response(
                {'error': f'Ask for at most {MAX_RANGE_DAYS} days at a time.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = CalendarService(
            request.user, start, end, start_date, end_date
        )
        return Response(service.payload())

    @staticmethod
    def _date(request, name):
        """A YYYY-MM-DD query param, None if absent, or a 400 response."""
        raw = request.query_params.get(name)
        if not raw:
            return None
        parsed = parse_date(raw)
        if parsed is None:
            return Response(
                {'error': f'`{name}` must be a date, as YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return parsed


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
