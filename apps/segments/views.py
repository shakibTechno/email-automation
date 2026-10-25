"""
Views for the Contact Segmentation app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from apps.contacts.models import Tag
from .models import Segment, SegmentMembership
from .serializers import (
    SegmentListSerializer,
    SegmentDetailSerializer,
    SegmentCreateSerializer,
    SegmentUpdateSerializer,
    SegmentMembershipSerializer,
    AddContactsSerializer,
    RemoveContactsSerializer,
    PreviewRulesSerializer,
    FieldDefinitionSerializer,
    SegmentContactSerializer,
    TagOptionSerializer,
)
from .services import SegmentService
from .evaluator import SegmentEvaluator, FIELD_DEFINITIONS, OPERATORS_BY_TYPE
from .filters import SegmentFilter


class SegmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contact segments.

    Endpoints:
    - GET /segments/ - List segments
    - POST /segments/ - Create segment
    - GET /segments/{id}/ - Get segment details
    - PATCH /segments/{id}/ - Update segment
    - DELETE /segments/{id}/ - Delete segment
    - POST /segments/{id}/refresh/ - Refresh contact count
    - POST /segments/{id}/duplicate/ - Duplicate segment
    - GET /segments/{id}/contacts/ - Get segment contacts
    - POST /segments/{id}/add-contacts/ - Add contacts (static only)
    - POST /segments/{id}/remove-contacts/ - Remove contacts (static only)
    - GET /segments/{id}/export/ - Export contacts as CSV
    - POST /segments/preview/ - Preview rules
    - GET /segments/field-definitions/ - Get available fields
    - GET /segments/tags/ - Get available tags
    """
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SegmentFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'contact_count', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Segment.objects.filter(
            organization=self.request.user.organization
        ).select_related('created_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return SegmentListSerializer
        elif self.action == 'create':
            return SegmentCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return SegmentUpdateSerializer
        return SegmentDetailSerializer

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """Refresh the cached contact count for a segment."""
        segment = self.get_object()
        count = SegmentService.refresh_segment_count(segment)
        return Response({
            'contact_count': count,
            'last_calculated_at': segment.last_calculated_at,
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a segment."""
        segment = self.get_object()
        new_segment = SegmentService.duplicate_segment(segment, user=request.user)
        serializer = SegmentDetailSerializer(new_segment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        """Get contacts in this segment with pagination."""
        segment = self.get_object()
        contacts_qs = SegmentService.get_segment_contacts(segment)

        # Simple pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        offset = (page - 1) * page_size

        total_count = contacts_qs.count()
        contacts = contacts_qs[offset:offset + page_size]

        serializer = SegmentContactSerializer(contacts, many=True)

        return Response({
            'results': serializer.data,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
        })

    @action(detail=True, methods=['post'], url_path='add-contacts')
    def add_contacts(self, request, pk=None):
        """Add contacts to a static segment."""
        segment = self.get_object()

        if not segment.is_static:
            return Response(
                {'error': 'Cannot manually add contacts to a dynamic segment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AddContactsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = SegmentService.add_contacts_to_segment(
            segment=segment,
            contact_ids=[str(cid) for cid in serializer.validated_data['contact_ids']],
            added_by=request.user,
        )

        return Response({
            'added': result['added'],
            'already_member': result['already_member'],
            'contact_count': segment.contact_count,
        })

    @action(detail=True, methods=['post'], url_path='remove-contacts')
    def remove_contacts(self, request, pk=None):
        """Remove contacts from a static segment."""
        segment = self.get_object()

        if not segment.is_static:
            return Response(
                {'error': 'Cannot manually remove contacts from a dynamic segment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RemoveContactsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        removed = SegmentService.remove_contacts_from_segment(
            segment=segment,
            contact_ids=[str(cid) for cid in serializer.validated_data['contact_ids']],
        )

        return Response({
            'removed': removed,
            'contact_count': segment.contact_count,
        })

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export segment contacts as CSV."""
        segment = self.get_object()
        csv_content = SegmentService.export_segment_contacts_csv(segment)

        response = HttpResponse(csv_content, content_type='text/csv')
        filename = f"segment_{segment.name.replace(' ', '_')}_{segment.id}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'])
    def preview(self, request):
        """Preview contacts matching rules without saving."""
        serializer = PreviewRulesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = SegmentService.preview_rules(
            organization=request.user.organization,
            rules=serializer.validated_data['rules'],
            limit=serializer.validated_data.get('limit', 100),
        )

        return Response(result)

    @action(detail=False, methods=['get'], url_path='field-definitions')
    def field_definitions(self, request):
        """
        Available fields and their operators for the segment builder.

        Organization-scoped now, so the customer's own custom fields appear in
        the list with their declared types. They were previously absent
        entirely — the builder read a module-level dict — which meant a custom
        field could only be used by someone who knew to type `custom.<key>` by
        hand, and then got string operators for it regardless of its type.
        """
        organization = request.user.organization
        fields = []

        definitions = SegmentEvaluator.get_field_definitions(organization)

        for field_key, field_def in definitions.items():
            operators = SegmentEvaluator.get_operators_for_field(
                field_key, organization=organization,
            )
            operator_list = [
                {'value': op[0], 'label': op[1]}
                for op in operators
            ]

            field_data = {
                'field': field_key,
                'type': field_def['type'],
                'label': field_def['label'],
                'operators': operator_list,
                # Lets the builder group the customer's own fields separately
                # from the built-in ones.
                'custom': field_def.get('custom', False),
            }

            if 'options' in field_def:
                field_data['options'] = field_def['options']

            fields.append(field_data)

        return Response(fields)

    @action(detail=False, methods=['get'])
    def tags(self, request):
        """Get available tags for the tag field selector."""
        tags = Tag.objects.filter(
            organization=request.user.organization
        ).order_by('name')

        serializer = TagOptionSerializer(tags, many=True)
        return Response(serializer.data)


class SegmentMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing segment memberships (static segments only).
    """
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = SegmentMembershipSerializer

    def get_queryset(self):
        segment_id = self.kwargs.get('segment_pk')
        return SegmentMembership.objects.filter(
            segment_id=segment_id,
            segment__organization=self.request.user.organization
        ).select_related('contact')
