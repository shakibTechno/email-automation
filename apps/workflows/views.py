"""
Views for the Workflow Automation app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import (
    Workflow,
    WorkflowExecution,
    WorkflowTemplate,
)
from .serializers import (
    WorkflowListSerializer,
    WorkflowSerializer,
    WorkflowCreateSerializer,
    WorkflowUpdateSerializer,
    WorkflowExecutionListSerializer,
    WorkflowExecutionSerializer,
    WorkflowTemplateListSerializer,
    WorkflowTemplateSerializer,
    WorkflowAnalyticsSerializer,
    WorkflowValidationSerializer,
)
from .filters import (
    WorkflowFilter,
    WorkflowExecutionFilter,
    WorkflowTemplateFilter,
)
from .services import WorkflowService


class WorkflowViewSet(viewsets.ModelViewSet):
    """ViewSet for Workflow CRUD operations and actions."""
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = WorkflowFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at', 'status', 'contacts_entered']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter workflows by organization."""
        return Workflow.objects.filter(
            organization=self.request.user.organization
        ).select_related('created_by').prefetch_related('nodes', 'edges')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return WorkflowListSerializer
        elif self.action == 'create':
            return WorkflowCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return WorkflowUpdateSerializer
        return WorkflowSerializer

    def perform_destroy(self, instance):
        """Soft delete the workflow."""
        instance.soft_delete()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a workflow after validation."""
        workflow = self.get_object()

        if workflow.status == 'active':
            return Response(
                {'detail': 'Workflow is already active.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, errors = WorkflowService.activate_workflow(workflow)

        if success:
            return Response({
                'detail': 'Workflow activated successfully.',
                'status': workflow.status,
            })
        else:
            return Response(
                {'detail': 'Workflow validation failed.', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate/pause a workflow."""
        workflow = self.get_object()

        if workflow.status != 'active':
            return Response(
                {'detail': 'Workflow is not active.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        WorkflowService.deactivate_workflow(workflow)

        return Response({
            'detail': 'Workflow deactivated successfully.',
            'status': workflow.status,
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a copy of a workflow."""
        workflow = self.get_object()
        new_workflow = WorkflowService.duplicate_workflow(
            workflow=workflow,
            user=request.user
        )

        serializer = WorkflowSerializer(new_workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def validate(self, request, pk=None):
        """Validate a workflow without activating it."""
        workflow = self.get_object()
        errors = WorkflowService.validate_workflow(workflow)

        data = {
            'is_valid': len(errors) == 0,
            'errors': errors,
        }
        serializer = WorkflowValidationSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get workflow analytics."""
        workflow = self.get_object()
        days = int(request.query_params.get('days', 30))

        analytics = WorkflowService.get_workflow_analytics(workflow, days=days)
        serializer = WorkflowAnalyticsSerializer(analytics)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get workflow executions."""
        workflow = self.get_object()

        # Apply filters
        executions = workflow.executions.select_related('contact', 'current_node')

        status_param = request.query_params.get('status')
        if status_param:
            executions = executions.filter(status=status_param)

        goal_reached = request.query_params.get('goal_reached')
        if goal_reached is not None:
            executions = executions.filter(goal_reached=goal_reached == 'true')

        # Paginate
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = WorkflowExecutionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = WorkflowExecutionListSerializer(executions, many=True)
        return Response(serializer.data)


class WorkflowExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing workflow executions."""
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = WorkflowExecutionFilter
    ordering_fields = ['started_at', 'completed_at', 'status']
    ordering = ['-started_at']

    def get_queryset(self):
        """Filter executions by organization."""
        return WorkflowExecution.objects.filter(
            workflow__organization=self.request.user.organization
        ).select_related('workflow', 'contact', 'current_node').prefetch_related('steps__node')

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowExecutionListSerializer
        return WorkflowExecutionSerializer

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running workflow execution."""
        execution = self.get_object()

        if execution.status in ('completed', 'cancelled', 'failed'):
            return Response(
                {'detail': f'Execution is already {execution.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.status = 'cancelled'
        execution.save(update_fields=['status', 'updated_at'])

        # Update workflow stats
        from django.db.models import F
        Workflow.objects.filter(id=execution.workflow_id).update(
            contacts_active=F('contacts_active') - 1
        )

        return Response({'detail': 'Execution cancelled.'})


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow templates."""
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = WorkflowTemplateFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'usage_count', 'created_at']
    ordering = ['-is_system', '-usage_count', 'name']

    def get_queryset(self):
        """Return system templates and organization's templates."""
        org = self.request.user.organization
        return WorkflowTemplate.objects.filter(
            is_active=True
        ).filter(
            # System templates OR organization's templates
            organization__isnull=True
        ) | WorkflowTemplate.objects.filter(
            is_active=True,
            organization=org
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowTemplateListSerializer
        return WorkflowTemplateSerializer

    def perform_create(self, serializer):
        """Set organization for user-created templates."""
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['post'])
    def use(self, request, pk=None):
        """Create a new workflow from this template."""
        template = self.get_object()

        workflow = WorkflowService.create_from_template(
            template=template,
            organization=request.user.organization,
            user=request.user,
        )

        serializer = WorkflowSerializer(workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
