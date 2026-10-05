"""
Views for the Lead Scoring app.
"""
import logging
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import ScoringRule, ScoreThreshold
from .permissions import LeadScoringEnabled
from .serializers import (
    ScoringRuleSerializer,
    ScoreThresholdSerializer,
    BulkUpdateThresholdsSerializer,
    ReorderRulesSerializer,
)

logger = logging.getLogger(__name__)


class ScoringRuleViewSet(viewsets.ModelViewSet):
    """
    CRUD for scoring rules. Restricted to Professional+ plans.

    Extra actions:
      POST /{id}/toggle/   — flip is_active
      POST /reorder/       — bulk-set priority order
    """
    serializer_class = ScoringRuleSerializer
    permission_classes = [
        IsAuthenticated,
        IsOrganizationMember,
        IsAdminForDestructiveActions,
        LeadScoringEnabled,
    ]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = ScoringRule.objects.filter(
            organization=self.request.user.organization,
            deleted_at__isnull=True,
        ).order_by('priority', 'name')

        rule_type = self.request.query_params.get('rule_type')
        if rule_type:
            qs = qs.filter(rule_type=rule_type)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        return qs

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    def perform_destroy(self, instance):
        instance.soft_delete()

    @extend_schema(
        description="Toggle the is_active flag on a scoring rule.",
        responses={200: ScoringRuleSerializer},
    )
    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save(update_fields=['is_active', 'updated_at'])
        return Response(ScoringRuleSerializer(rule).data)

    @extend_schema(
        description="Bulk-update rule priorities by supplying an ordered list of IDs.",
        request=ReorderRulesSerializer,
        responses={200: {'description': 'Rules reordered'}},
    )
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        serializer = ReorderRulesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ordered_ids = serializer.validated_data['ordered_ids']

        org = request.user.organization
        with transaction.atomic():
            for priority, rule_id in enumerate(ordered_ids):
                ScoringRule.objects.filter(
                    id=rule_id, organization=org
                ).update(priority=priority)

        return Response({'message': f'{len(ordered_ids)} rules reordered.'})


class ScoreThresholdViewSet(viewsets.ModelViewSet):
    """
    CRUD for score thresholds. Restricted to Professional+ plans.

    Extra action:
      POST /bulk-update/  — atomically replace all org thresholds
    """
    serializer_class = ScoreThresholdSerializer
    permission_classes = [
        IsAuthenticated,
        IsOrganizationMember,
        IsAdminForDestructiveActions,
        LeadScoringEnabled,
    ]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return ScoreThreshold.objects.filter(
            organization=self.request.user.organization
        ).order_by('min_score')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @extend_schema(
        description=(
            "Atomically replace all score thresholds for the organization. "
            "Deletes existing thresholds and creates the supplied set in one transaction."
        ),
        request=BulkUpdateThresholdsSerializer,
        responses={200: ScoreThresholdSerializer(many=True)},
    )
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        serializer = BulkUpdateThresholdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org = request.user.organization
        threshold_data = serializer.validated_data['thresholds']

        with transaction.atomic():
            ScoreThreshold.objects.filter(organization=org).delete()
            created = ScoreThreshold.objects.bulk_create([
                ScoreThreshold(
                    organization=org,
                    label=t['label'],
                    min_score=t['min_score'],
                    color=t.get('color', 'blue'),
                    engagement_level=t['engagement_level'],
                )
                for t in threshold_data
            ])

        return Response(
            ScoreThresholdSerializer(created, many=True).data,
            status=status.HTTP_200_OK,
        )
