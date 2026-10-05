from django_filters import rest_framework as filters
from .models import EmailSequence, SequenceEnrollment


class SequenceFilter(filters.FilterSet):
    status = filters.CharFilter(field_name='status')
    search = filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = EmailSequence
        fields = ['status']


class SequenceEnrollmentFilter(filters.FilterSet):
    status = filters.CharFilter(field_name='status')
    contact = filters.UUIDFilter(field_name='contact__id')
    sequence = filters.UUIDFilter(field_name='sequence__id')

    class Meta:
        model = SequenceEnrollment
        fields = ['status', 'contact', 'sequence']
