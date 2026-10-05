"""
Filters for the Email Campaigns app.
"""
from django_filters import rest_framework as filters
from .models import Campaign


class CampaignFilter(filters.FilterSet):
    """FilterSet for Campaign model."""

    status = filters.ChoiceFilter(choices=Campaign.STATUS_CHOICES)
    created_after = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='gte'
    )
    created_before = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='lte'
    )
    scheduled_after = filters.DateTimeFilter(
        field_name='scheduled_at', lookup_expr='gte'
    )
    scheduled_before = filters.DateTimeFilter(
        field_name='scheduled_at', lookup_expr='lte'
    )

    class Meta:
        model = Campaign
        fields = ['status']
