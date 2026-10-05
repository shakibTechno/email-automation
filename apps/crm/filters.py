"""
Filters for the CRM & Pipeline app.
"""
from django_filters import rest_framework as filters
from .models import Deal, Activity, CRMTask, Company


class DealFilter(filters.FilterSet):
    """FilterSet for Deal model."""

    status = filters.ChoiceFilter(choices=Deal.STATUS_CHOICES)
    pipeline = filters.UUIDFilter(field_name='pipeline_id')
    stage = filters.UUIDFilter(field_name='stage_id')
    assigned_to = filters.UUIDFilter(field_name='assigned_to_id')
    priority = filters.ChoiceFilter(choices=Deal.PRIORITY_CHOICES)
    close_date_after = filters.DateFilter(field_name='close_date', lookup_expr='gte')
    close_date_before = filters.DateFilter(field_name='close_date', lookup_expr='lte')
    min_value = filters.NumberFilter(field_name='value', lookup_expr='gte')
    max_value = filters.NumberFilter(field_name='value', lookup_expr='lte')
    primary_contact = filters.UUIDFilter(field_name='primary_contact_id')
    is_rotting = filters.BooleanFilter()

    class Meta:
        model = Deal
        fields = ['status', 'pipeline', 'stage', 'assigned_to', 'priority', 'is_rotting']


class ActivityFilter(filters.FilterSet):
    """FilterSet for Activity model."""

    activity_type = filters.ChoiceFilter(choices=Activity.ACTIVITY_TYPE_CHOICES)
    deal = filters.UUIDFilter(field_name='deal_id')
    contact = filters.UUIDFilter(field_name='contact_id')
    is_completed = filters.BooleanFilter()
    due_after = filters.DateTimeFilter(field_name='due_date', lookup_expr='gte')
    due_before = filters.DateTimeFilter(field_name='due_date', lookup_expr='lte')
    assigned_to = filters.UUIDFilter(field_name='assigned_to_id')

    class Meta:
        model = Activity
        fields = ['activity_type', 'deal', 'contact', 'is_completed']


class CRMTaskFilter(filters.FilterSet):
    """FilterSet for CRMTask model."""

    status = filters.ChoiceFilter(choices=CRMTask.STATUS_CHOICES)
    priority = filters.ChoiceFilter(choices=CRMTask.PRIORITY_CHOICES)
    deal = filters.UUIDFilter(field_name='deal_id')
    contact = filters.UUIDFilter(field_name='contact_id')
    assigned_to = filters.UUIDFilter(field_name='assigned_to_id')
    due_after = filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_before = filters.DateFilter(field_name='due_date', lookup_expr='lte')
    is_overdue = filters.BooleanFilter(method='filter_overdue')

    class Meta:
        model = CRMTask
        fields = ['status', 'priority', 'deal', 'contact', 'assigned_to']

    def filter_overdue(self, queryset, name, value):
        from django.utils.timezone import now
        today = now().date()
        if value:
            return queryset.filter(due_date__lt=today, status__in=['todo', 'in_progress'])
        return queryset.exclude(due_date__lt=today, status__in=['todo', 'in_progress'])


class CompanyFilter(filters.FilterSet):
    """FilterSet for Company model."""
    industry = filters.ChoiceFilter(choices=Company.INDUSTRY_CHOICES)
    size = filters.ChoiceFilter(choices=Company.SIZE_CHOICES)
    owner = filters.UUIDFilter(field_name='owner_id')

    class Meta:
        model = Company
        fields = ['industry', 'size', 'owner']
