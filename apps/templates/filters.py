"""
Filters for the Email Templates app.
"""
from django_filters import rest_framework as filters
from .models import EmailTemplate


class EmailTemplateFilter(filters.FilterSet):
    """Filter for EmailTemplate model."""

    category = filters.ChoiceFilter(choices=EmailTemplate.CATEGORY_CHOICES)
    is_preset = filters.BooleanFilter()
    is_active = filters.BooleanFilter()

    class Meta:
        model = EmailTemplate
        fields = ['category', 'is_preset', 'is_active']
