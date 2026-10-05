"""
Filters for the Landing Pages app.
"""
from django_filters import rest_framework as filters

from .models import LandingPage, LandingPageTemplate


class LandingPageFilter(filters.FilterSet):
    """FilterSet for LandingPage model."""

    status = filters.ChoiceFilter(choices=LandingPage.STATUS_CHOICES)
    has_form = filters.BooleanFilter(method='filter_has_form')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = LandingPage
        fields = ['status', 'has_form', 'created_after', 'created_before']

    def filter_has_form(self, queryset, name, value):
        if value is True:
            return queryset.filter(form__isnull=False)
        elif value is False:
            return queryset.filter(form__isnull=True)
        return queryset


class LandingPageTemplateFilter(filters.FilterSet):
    """FilterSet for LandingPageTemplate model."""

    category = filters.ChoiceFilter(choices=LandingPageTemplate.CATEGORY_CHOICES)
    is_system = filters.BooleanFilter()

    class Meta:
        model = LandingPageTemplate
        fields = ['category', 'is_system']
