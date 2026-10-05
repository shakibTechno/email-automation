"""
Filters for the Workflow Automation app.
"""
from django_filters import rest_framework as filters
from .models import Workflow, WorkflowExecution, WorkflowTemplate


class WorkflowFilter(filters.FilterSet):
    """Filter for Workflow model."""
    status = filters.ChoiceFilter(choices=Workflow.STATUS_CHOICES)
    name = filters.CharFilter(lookup_expr='icontains')
    created_at_gte = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at_lte = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Workflow
        fields = ['status', 'name']


class WorkflowExecutionFilter(filters.FilterSet):
    """Filter for WorkflowExecution model."""
    status = filters.ChoiceFilter(choices=WorkflowExecution.STATUS_CHOICES)
    goal_reached = filters.BooleanFilter()
    started_at_gte = filters.DateTimeFilter(field_name='started_at', lookup_expr='gte')
    started_at_lte = filters.DateTimeFilter(field_name='started_at', lookup_expr='lte')
    contact = filters.UUIDFilter()

    class Meta:
        model = WorkflowExecution
        fields = ['status', 'goal_reached', 'contact']


class WorkflowTemplateFilter(filters.FilterSet):
    """Filter for WorkflowTemplate model."""
    category = filters.ChoiceFilter(choices=WorkflowTemplate.CATEGORY_CHOICES)
    is_system = filters.BooleanFilter()
    is_active = filters.BooleanFilter()
    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = WorkflowTemplate
        fields = ['category', 'is_system', 'is_active', 'name']
