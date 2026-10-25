"""
Landlord console API.

Every view here reads across all tenants. They inherit from the base classes in
viewsets.py, which carry IsPlatformStaff — do not set permission_classes to
anything looser, and do not add a view that bypasses those bases.
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Organization

from .services import (
    DeliverabilityService,
    PlatformOverviewService,
    RevenueService,
    SuspensionService,
    TenantService,
)
from .viewsets import PlatformScopedAPIView, PlatformScopedViewSet

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 100


class PlatformOverviewView(PlatformScopedAPIView):
    """GET /api/v1/landlord/overview/ — platform totals and trends."""

    def get(self, request):
        try:
            days = max(1, min(int(request.query_params.get('days', 30)), 365))
        except (TypeError, ValueError):
            days = 30
        # `refresh=1` skips the cache, for when an operator has just changed
        # something and wants to see it immediately.
        use_cache = request.query_params.get('refresh') not in ('1', 'true')
        return Response(PlatformOverviewService.get_overview(days, use_cache=use_cache))


class DeliverabilityView(PlatformScopedAPIView):
    """GET /api/v1/landlord/deliverability/ — tenants ranked by risk to the shared IP."""

    def get(self, request):
        rows = DeliverabilityService.get_risk_board()
        return Response({
            'count': len(rows),
            'at_risk': sum(1 for r in rows if r['over_threshold']),
            'results': rows,
        })


class RevenueView(PlatformScopedAPIView):
    """GET /api/v1/landlord/revenue/ — MRR, plan mix, trials, at-risk accounts."""

    def get(self, request):
        return Response(RevenueService.get_revenue())


class TenantViewSet(PlatformScopedViewSet):
    """
    /api/v1/landlord/tenants/ — every organization on the platform.

    Read, suspend and restore only. Editing a tenant's data belongs in Django
    admin, where it is at least obvious that is what you are doing.
    """

    def list(self, request):
        queryset = TenantService.base_queryset()

        search = (request.query_params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        plan = request.query_params.get('plan')
        if plan:
            queryset = queryset.filter(plan=plan)

        tenant_status = request.query_params.get('status')
        if tenant_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif tenant_status == 'suspended':
            queryset = queryset.filter(is_active=False)

        total = queryset.count()
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            per_page = min(int(request.query_params.get('per_page', 25)), MAX_PAGE_SIZE)
        except (TypeError, ValueError):
            page, per_page = 1, 25

        start = (page - 1) * per_page
        rows = [TenantService.serialize_row(o) for o in queryset[start:start + per_page]]

        return Response({
            'results': rows,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
        })

    def retrieve(self, request, pk=None):
        org = get_object_or_404(Organization.all_objects, pk=pk)
        return Response(TenantService.get_detail(org))

    @action(detail=True, methods=['post'], url_path='suspend-sending')
    def suspend_sending(self, request, pk=None):
        org = get_object_or_404(Organization.all_objects, pk=pk)
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'error': 'A reason is required — the tenant is told why, and it is logged.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        SuspensionService.suspend_sending(org, reason, actor=request.user)
        return Response(TenantService.get_detail(org))

    @action(detail=True, methods=['post'], url_path='resume-sending')
    def resume_sending(self, request, pk=None):
        org = get_object_or_404(Organization.all_objects, pk=pk)
        SuspensionService.resume_sending(org, actor=request.user)
        return Response(TenantService.get_detail(org))

    @action(detail=True, methods=['post'], url_path='suspend-account')
    def suspend_account(self, request, pk=None):
        org = get_object_or_404(Organization.all_objects, pk=pk)
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'error': 'A reason is required — the tenant sees it when login is refused.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        SuspensionService.suspend_account(org, reason, actor=request.user)
        return Response(TenantService.get_detail(org))

    @action(detail=True, methods=['post'], url_path='restore-account')
    def restore_account(self, request, pk=None):
        org = get_object_or_404(Organization.all_objects, pk=pk)
        # Access and sending are restored together by default, but a tenant
        # suspended for a deliverability problem may need its data back while
        # its mail stays stopped.
        resume = request.data.get('resume_sending', True)
        SuspensionService.restore_account(org, actor=request.user, resume_sending=bool(resume))
        return Response(TenantService.get_detail(org))
