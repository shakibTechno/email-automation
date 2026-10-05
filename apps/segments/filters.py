"""
Filters for the Contact Segmentation app.
"""
import django_filters
from .models import Segment


class SegmentFilter(django_filters.FilterSet):
    """Filter for segment list."""

    segment_type = django_filters.ChoiceFilter(
        choices=Segment.SEGMENT_TYPE_CHOICES
    )
    name = django_filters.CharFilter(lookup_expr='icontains')
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    min_contacts = django_filters.NumberFilter(
        field_name='contact_count',
        lookup_expr='gte'
    )
    max_contacts = django_filters.NumberFilter(
        field_name='contact_count',
        lookup_expr='lte'
    )

    class Meta:
        model = Segment
        fields = ['segment_type', 'name']
