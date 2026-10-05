"""
Admin configuration for the Workflows app.
"""
from django.contrib import admin
from .models import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTemplate,
)


class WorkflowNodeInline(admin.TabularInline):
    """Inline admin for workflow nodes."""
    model = WorkflowNode
    extra = 0
    readonly_fields = ('id', 'created_at')
    fields = ('id', 'node_type', 'label', 'position_x', 'position_y', 'created_at')


class WorkflowEdgeInline(admin.TabularInline):
    """Inline admin for workflow edges."""
    model = WorkflowEdge
    extra = 0
    readonly_fields = ('id', 'created_at')
    fields = ('id', 'source_node', 'target_node', 'edge_type', 'created_at')


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin for Workflow model."""
    list_display = (
        'name', 'organization', 'status', 'contacts_entered',
        'contacts_completed', 'activated_at', 'created_at'
    )
    list_filter = ('status', 'organization', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = (
        'id', 'contacts_entered', 'contacts_active', 'contacts_completed',
        'contacts_goal_reached', 'created_at', 'updated_at'
    )
    inlines = [WorkflowNodeInline, WorkflowEdgeInline]
    raw_id_fields = ('organization', 'created_by')


@admin.register(WorkflowNode)
class WorkflowNodeAdmin(admin.ModelAdmin):
    """Admin for WorkflowNode model."""
    list_display = ('label', 'workflow', 'node_type', 'position_x', 'position_y', 'created_at')
    list_filter = ('node_type', 'workflow__organization')
    search_fields = ('label', 'workflow__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('workflow',)


@admin.register(WorkflowEdge)
class WorkflowEdgeAdmin(admin.ModelAdmin):
    """Admin for WorkflowEdge model."""
    list_display = ('workflow', 'source_node', 'target_node', 'edge_type', 'created_at')
    list_filter = ('edge_type', 'workflow__organization')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('workflow', 'source_node', 'target_node')


class WorkflowExecutionStepInline(admin.TabularInline):
    """Inline admin for execution steps."""
    model = WorkflowExecutionStep
    extra = 0
    readonly_fields = ('id', 'node', 'status', 'started_at', 'completed_at', 'branch_taken')
    fields = ('id', 'node', 'status', 'started_at', 'completed_at', 'branch_taken')


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    """Admin for WorkflowExecution model."""
    list_display = (
        'workflow', 'contact', 'status', 'goal_reached',
        'started_at', 'completed_at'
    )
    list_filter = ('status', 'goal_reached', 'workflow__organization')
    search_fields = ('workflow__name', 'contact__email')
    readonly_fields = (
        'id', 'started_at', 'completed_at', 'goal_reached_at',
        'created_at', 'updated_at'
    )
    inlines = [WorkflowExecutionStepInline]
    raw_id_fields = ('workflow', 'contact', 'current_node')


@admin.register(WorkflowExecutionStep)
class WorkflowExecutionStepAdmin(admin.ModelAdmin):
    """Admin for WorkflowExecutionStep model."""
    list_display = ('execution', 'node', 'status', 'branch_taken', 'started_at', 'completed_at')
    list_filter = ('status', 'branch_taken')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('execution', 'node')


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    """Admin for WorkflowTemplate model."""
    list_display = ('name', 'category', 'is_system', 'is_active', 'usage_count', 'created_at')
    list_filter = ('category', 'is_system', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'usage_count', 'created_at', 'updated_at')
    raw_id_fields = ('organization',)
