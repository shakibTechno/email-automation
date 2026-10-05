"""
Filters for the Forms & Lead Capture app.
"""
from django_filters import rest_framework as filters
from .models import Form


class FormFilter(filters.FilterSet):
    """FilterSet for Form model."""

    status = filters.ChoiceFilter(choices=Form.STATUS_CHOICES)
    form_type = filters.ChoiceFilter(choices=Form.FORM_TYPE_CHOICES)
    created_after = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='gte'
    )
    created_before = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='lte'
    )

    class Meta:
        model = Form
        fields = ['status', 'form_type']
