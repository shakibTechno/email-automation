"""
Views for the CRM & Pipeline app.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import Pipeline, Stage, Deal, DealContact, Activity, CRMTask, Company
from .serializers import (
    PipelineListSerializer,
    PipelineSerializer,
    PipelineCreateSerializer,
    StageSerializer,
    StageCreateSerializer,
    StageReorderSerializer,
    DealListSerializer,
    DealSerializer,
    DealCreateSerializer,
    DealUpdateSerializer,
    DealMoveSerializer,
    DealWinSerializer,
    DealLoseSerializer,
    DealKanbanSerializer,
    KanbanStageSerializer,
    DealContactSerializer,
    DealContactCreateSerializer,
    ActivityListSerializer,
    ActivitySerializer,
    ActivityCreateSerializer,
    DealStageHistorySerializer,
    PipelineAnalyticsSerializer,
    CRMTaskListSerializer,
    CRMTaskSerializer,
    CRMTaskCreateSerializer,
    ForecastSerializer,
    CompanyListSerializer,
    CompanySerializer,
    CompanyCreateSerializer,
)
from .filters import DealFilter, ActivityFilter, CRMTaskFilter, CompanyFilter
from .services import PipelineService, DealService, ActivityService, CRMAnalyticsService, CRMTaskService, ForecastingService, CompanyService

logger = logging.getLogger(__name__)


class PipelineViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Pipeline model.

    Provides CRUD and additional actions:
    - kanban: Get kanban board data
    - analytics: Get pipeline analytics
    - add_stage: Add a stage to the pipeline
    - reorder_stages: Reorder stages
    - remove_stage: Remove a stage
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]

    def get_queryset(self):
        return Pipeline.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related('stages')

    def get_serializer_class(self):
        if self.action == 'list':
            return PipelineListSerializer
        elif self.action == 'create':
            return PipelineCreateSerializer
        return PipelineSerializer

    def perform_create(self, serializer):
        # If this is the first pipeline, make it default
        org = self.request.user.organization
        is_default = not Pipeline.objects.filter(organization=org).exists()
        serializer.save(
            organization=org,
            created_by=self.request.user,
            is_default=is_default,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            return Response(
                {'error': 'Cannot delete the default pipeline.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def kanban(self, request, pk=None):
        """Get kanban board data for a pipeline."""
        pipeline = self.get_object()
        kanban_data = DealService.get_kanban_data(pipeline)
        serializer = KanbanStageSerializer(kanban_data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for a pipeline."""
        pipeline = self.get_object()
        org = request.user.organization
        days = int(request.query_params.get('days', 30))

        data = {
            'value_by_stage': CRMAnalyticsService.get_pipeline_value_by_stage(pipeline),
            'win_rate': CRMAnalyticsService.get_win_rate(org, days),
            'avg_deal_size': CRMAnalyticsService.get_average_deal_size(org, days),
            'conversion_rates': CRMAnalyticsService.get_conversion_rates(pipeline, days),
            'summary': CRMAnalyticsService.get_pipeline_summary(org, days),
        }

        serializer = PipelineAnalyticsSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add_stage')
    def add_stage(self, request, pk=None):
        """Add a new stage to the pipeline."""
        pipeline = self.get_object()
        serializer = StageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get next position
        max_pos = pipeline.stages.aggregate(
            max_pos=models.Max('position')
        )['max_pos']
        position = (max_pos + 1) if max_pos is not None else 0

        stage = Stage.objects.create(
            pipeline=pipeline,
            position=position,
            **serializer.validated_data
        )

        return Response(
            StageSerializer(stage).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='reorder_stages')
    def reorder_stages(self, request, pk=None):
        """Reorder stages in the pipeline."""
        pipeline = self.get_object()
        serializer = StageReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        PipelineService.reorder_stages(pipeline, serializer.validated_data['stage_ids'])

        # Return updated pipeline
        pipeline.refresh_from_db()
        return Response(PipelineSerializer(pipeline).data)

    @action(detail=False, methods=['get'])
    def forecast(self, request):
        """Revenue forecast grouped by close month."""
        org = request.user.organization
        data = ForecastingService.get_forecast(org)
        serializer = ForecastSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='stages/(?P<stage_pk>[^/.]+)')
    def remove_stage(self, request, pk=None, stage_pk=None):
        """Remove a stage from the pipeline."""
        pipeline = self.get_object()
        try:
            stage = pipeline.stages.get(pk=stage_pk)
        except Stage.DoesNotExist:
            return Response(
                {'error': 'Stage not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Block deletion if stage has deals
        if stage.deals.exists():
            return Response(
                {'error': 'Cannot delete a stage that contains deals. Move or delete the deals first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        stage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Import models for Max aggregation
from django.db import models


class DealViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Deal model.

    Provides CRUD and additional actions:
    - move: Move deal to a different stage
    - win: Mark deal as won
    - lose: Mark deal as lost
    - reopen: Reopen a closed deal
    - contacts: List/add contacts
    - remove_contact: Remove a contact
    - activities: List/add activities
    - history: Get stage history
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DealFilter
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'value', 'priority', 'close_date', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Deal.objects.filter(
            organization=self.request.user.organization
        ).select_related('pipeline', 'stage', 'primary_contact', 'assigned_to', 'created_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return DealListSerializer
        elif self.action == 'create':
            return DealCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DealUpdateSerializer
        return DealSerializer

    def perform_create(self, serializer):
        data = serializer.validated_data.copy()
        contact_ids = data.pop('contact_ids', [])

        # If no stage specified, use first open stage of pipeline
        pipeline = data.get('pipeline')
        if not data.get('stage') and pipeline:
            first_stage = pipeline.stages.filter(stage_type='open').order_by('position').first()
            if first_stage:
                data['stage'] = first_stage

        # Set probability from stage default if not explicitly set
        if 'probability' not in self.request.data and data.get('stage'):
            data['probability'] = data['stage'].default_probability

        data['contact_ids'] = contact_ids
        DealService.create_deal(
            organization=self.request.user.organization,
            data=data,
            created_by=self.request.user,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        DealService.update_pipeline_stats(instance.pipeline)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Move deal to a different stage."""
        deal = self.get_object()
        serializer = DealMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        deal = DealService.move_deal(
            deal,
            serializer.validated_data['stage_id'],
            moved_by=request.user,
            position=serializer.validated_data.get('position'),
        )

        return Response(DealSerializer(deal).data)

    @action(detail=True, methods=['post'])
    def win(self, request, pk=None):
        """Mark deal as won."""
        deal = self.get_object()
        serializer = DealWinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        deal = DealService.win_deal(
            deal,
            win_reason=serializer.validated_data.get('win_reason', ''),
            closed_by=request.user,
        )

        return Response(DealSerializer(deal).data)

    @action(detail=True, methods=['post'])
    def lose(self, request, pk=None):
        """Mark deal as lost."""
        deal = self.get_object()
        serializer = DealLoseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        deal = DealService.lose_deal(
            deal,
            loss_reason=serializer.validated_data.get('loss_reason', ''),
            closed_by=request.user,
        )

        return Response(DealSerializer(deal).data)

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Reopen a closed deal."""
        deal = self.get_object()
        to_stage_id = request.data.get('stage_id')

        deal = DealService.reopen_deal(deal, to_stage_id=to_stage_id)

        return Response(DealSerializer(deal).data)

    @action(detail=True, methods=['get', 'post'])
    def contacts(self, request, pk=None):
        """List or add contacts for a deal."""
        deal = self.get_object()

        if request.method == 'GET':
            dc = deal.deal_contacts.select_related('contact').all()
            serializer = DealContactSerializer(dc, many=True)
            return Response(serializer.data)

        # POST: add contact
        serializer = DealContactCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dc, created = DealContact.objects.get_or_create(
            deal=deal,
            contact_id=serializer.validated_data['contact_id'],
            defaults={
                'role': serializer.validated_data['role'],
                'is_primary': serializer.validated_data['is_primary'],
            }
        )

        if not created:
            return Response(
                {'error': 'Contact is already linked to this deal.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            DealContactSerializer(dc).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path='contacts/(?P<contact_pk>[^/.]+)')
    def remove_contact(self, request, pk=None, contact_pk=None):
        """Remove a contact from a deal."""
        deal = self.get_object()
        try:
            dc = deal.deal_contacts.get(contact_id=contact_pk)
        except DealContact.DoesNotExist:
            return Response(
                {'error': 'Contact not found on this deal.'},
                status=status.HTTP_404_NOT_FOUND
            )
        dc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'])
    def activities(self, request, pk=None):
        """List or create activities for a deal."""
        deal = self.get_object()

        if request.method == 'GET':
            activities = deal.activities.select_related(
                'created_by', 'assigned_to', 'contact'
            ).order_by('-created_at')
            serializer = ActivityListSerializer(activities, many=True)
            return Response(serializer.data)

        # POST: create activity
        serializer = ActivityCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        data = {k: v for k, v in serializer.validated_data.items() if k != 'deal'}
        data['deal'] = deal
        activity = ActivityService.log_activity(
            organization=request.user.organization,
            data=data,
            created_by=request.user,
        )

        return Response(
            ActivitySerializer(activity).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get stage history for a deal."""
        deal = self.get_object()
        history = deal.stage_history.select_related(
            'from_stage', 'to_stage', 'moved_by'
        ).order_by('-created_at')
        serializer = DealStageHistorySerializer(history, many=True)
        return Response(serializer.data)


class ActivityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Activity model.

    Provides CRUD and additional actions:
    - complete: Mark activity as completed
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ActivityFilter
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'activity_type', 'due_date', 'is_completed', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Activity.objects.filter(
            organization=self.request.user.organization
        ).select_related('deal', 'contact', 'created_by', 'assigned_to')

    def get_serializer_class(self):
        if self.action == 'list':
            return ActivityListSerializer
        elif self.action == 'create':
            return ActivityCreateSerializer
        return ActivitySerializer

    def create(self, request, *args, **kwargs):
        serializer = ActivityCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        activity = ActivityService.log_activity(
            organization=request.user.organization,
            data=dict(serializer.validated_data),
            created_by=request.user,
        )
        return Response(ActivitySerializer(activity).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark activity as completed."""
        activity = self.get_object()
        activity = ActivityService.complete_activity(activity)
        return Response(ActivitySerializer(activity).data)


class CRMTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRMTask model.
    Provides CRUD + complete action.
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CRMTaskFilter
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'priority', 'status', 'due_date', 'created_at']
    ordering = ['due_date', '-created_at']

    def get_queryset(self):
        return CRMTask.objects.filter(
            organization=self.request.user.organization
        ).select_related('deal', 'contact', 'assigned_to', 'created_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return CRMTaskListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CRMTaskCreateSerializer
        return CRMTaskSerializer

    def perform_create(self, serializer):
        CRMTaskService.create_task(
            organization=self.request.user.organization,
            data=serializer.validated_data,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark task as done."""
        task = self.get_object()
        task = CRMTaskService.complete_task(task)
        return Response(CRMTaskSerializer(task).data)


class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Company / Account model.

    Provides CRUD and sub-resource actions:
    - contacts: List contacts linked to this company
    - deals: List deals linked to this company
    - activities: List recent activities for this company
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CompanyFilter
    search_fields = ['name', 'domain', 'website']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        return Company.objects.filter(
            organization=self.request.user.organization
        ).select_related('owner')

    def get_serializer_class(self):
        if self.action == 'list':
            return CompanyListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CompanyCreateSerializer
        return CompanySerializer

    def create(self, request, *args, **kwargs):
        serializer = CompanyCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        company = CompanyService.create_company(
            organization=request.user.organization,
            data=dict(serializer.validated_data),
            created_by=request.user,
        )
        return Response(CompanySerializer(company).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        """List contacts associated with this company."""
        company = self.get_object()
        from apps.contacts.serializers import ContactListSerializer
        contacts = CompanyService.get_contacts(company)
        serializer = ContactListSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def deals(self, request, pk=None):
        """List deals associated with this company."""
        company = self.get_object()
        deals = CompanyService.get_deals(company)
        serializer = DealListSerializer(deals, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """List recent activities associated with this company."""
        company = self.get_object()
        activities = CompanyService.get_activities(company)
        serializer = ActivityListSerializer(activities, many=True)
        return Response(serializer.data)
