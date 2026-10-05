"""
Filters for the Contact app.
"""
from django_filters import rest_framework as filters
from .models import Contact, Tag


class ContactFilter(filters.FilterSet):
    """Filter for Contact model."""

    # Text search filters
    email = filters.CharFilter(lookup_expr='icontains')
    first_name = filters.CharFilter(lookup_expr='icontains')
    last_name = filters.CharFilter(lookup_expr='icontains')
    company = filters.CharFilter(lookup_expr='icontains')
    phone = filters.CharFilter(lookup_expr='icontains')
    job_title = filters.CharFilter(lookup_expr='icontains')

    # Search across multiple fields
    search = filters.CharFilter(method='filter_search')

    # Exact match filters
    is_subscribed = filters.BooleanFilter()
    is_verified = filters.BooleanFilter()
    engagement_level = filters.ChoiceFilter(choices=Contact.ENGAGEMENT_LEVEL_CHOICES)
    source = filters.ChoiceFilter(choices=Contact.SOURCE_CHOICES)

    # Tag filters
    tags = filters.ModelMultipleChoiceFilter(
        field_name='contact_tags__tag',
        queryset=Tag.objects.all(),
        label='Tags'
    )
    tag_names = filters.CharFilter(
        method='filter_tag_names',
        label='Tag Names (comma-separated)'
    )

    # Date range filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    last_activity_after = filters.DateTimeFilter(
        field_name='last_activity_at',
        lookup_expr='gte'
    )
    last_activity_before = filters.DateTimeFilter(
        field_name='last_activity_at',
        lookup_expr='lte'
    )

    # Lead score filters
    lead_score_min = filters.NumberFilter(field_name='lead_score', lookup_expr='gte')
    lead_score_max = filters.NumberFilter(field_name='lead_score', lookup_expr='lte')

    # Custom field filters
    custom_field = filters.CharFilter(method='filter_custom_field')

    # Bounced/Unsubscribed filters
    is_bounced = filters.BooleanFilter(method='filter_is_bounced')
    is_unsubscribed = filters.BooleanFilter(method='filter_is_unsubscribed')

    # Assignment filter
    assigned_to = filters.UUIDFilter(field_name='assigned_to_id')
    unassigned = filters.BooleanFilter(method='filter_unassigned')

    class Meta:
        model = Contact
        fields = [
            'email', 'first_name', 'last_name', 'company', 'phone',
            'job_title', 'is_subscribed', 'is_verified',
            'engagement_level', 'source', 'assigned_to'
        ]

    def filter_search(self, queryset, name, value):
        """
        Search across multiple fields: email, first_name, last_name, company.
        """
        return queryset.filter(
            models.Q(email__icontains=value) |
            models.Q(first_name__icontains=value) |
            models.Q(last_name__icontains=value) |
            models.Q(company__icontains=value) |
            models.Q(phone__icontains=value)
        )

    def filter_tag_names(self, queryset, name, value):
        """
        Filter by tag names (comma-separated).
        """
        if not value:
            return queryset

        tag_names = [tag.strip() for tag in value.split(',')]
        return queryset.filter(
            contact_tags__tag__name__in=tag_names
        ).distinct()

    def filter_custom_field(self, queryset, name, value):
        """
        Filter by custom field values.
        Format: field_name:field_value
        Example: ?custom_field=department:sales
        """
        if ':' not in value:
            return queryset

        field_name, field_value = value.split(':', 1)
        return queryset.filter(
            custom_fields__has_key=field_name
        ).filter(
            **{f'custom_fields__{field_name}__icontains': field_value}
        )

    def filter_is_bounced(self, queryset, name, value):
        """Filter contacts that have bounced."""
        if value:
            return queryset.exclude(bounced_at__isnull=True)
        return queryset.filter(bounced_at__isnull=True)

    def filter_is_unsubscribed(self, queryset, name, value):
        """Filter contacts that have unsubscribed."""
        if value:
            return queryset.filter(is_subscribed=False)
        return queryset.filter(is_subscribed=True)

    def filter_unassigned(self, queryset, name, value):
        if value:
            return queryset.filter(assigned_to__isnull=True)
        return queryset.filter(assigned_to__isnull=False)


# Import models for Q objects
from django.db import models
