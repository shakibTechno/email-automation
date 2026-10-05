"""
Views for the Contact app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import Contact, Tag, ContactTag, CustomField
from .serializers import (
    ContactSerializer,
    ContactListSerializer,
    ContactCreateSerializer,
    ContactUpdateSerializer,
    TagSerializer,
    CustomFieldSerializer,
    BulkDeleteSerializer,
    BulkTagSerializer,
    ContactImportSerializer,
)
from .filters import ContactFilter
from .services import CSVExportService, CSVImportService, DuplicateDetectionService
import logging

logger = logging.getLogger(__name__)


class ContactViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Contact model.

    Provides CRUD operations and additional actions:
    - bulk_delete: Delete multiple contacts
    - bulk_tag: Add/remove tags from multiple contacts
    - export: Export contacts to CSV
    - import_csv: Import contacts from CSV
    - duplicates: Find duplicate contacts
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContactFilter
    search_fields = ['email', 'first_name', 'last_name', 'company', 'phone']
    ordering_fields = [
        'email', 'first_name', 'last_name', 'company',
        'lead_score', 'engagement_level', 'created_at',
        'last_activity_at'
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        """Return contacts for the user's organization."""
        return Contact.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related('contact_tags__tag')

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return ContactListSerializer
        elif self.action == 'create':
            return ContactCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ContactUpdateSerializer
        return ContactSerializer

    @extend_schema(
        description="List all contacts with filtering, search, and pagination",
        parameters=[
            OpenApiParameter(
                name='search',
                description='Search across email, name, company, phone',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='is_subscribed',
                description='Filter by subscription status',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='engagement_level',
                description='Filter by engagement level',
                required=False,
                type=str
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List contacts with pagination."""
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Set organization from the authenticated user."""
        serializer.save(organization=self.request.user.organization)

    @extend_schema(description="Create a new contact")
    def create(self, request, *args, **kwargs):
        """Create a new contact."""
        return super().create(request, *args, **kwargs)

    @extend_schema(description="Retrieve a contact by ID")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a contact."""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(description="Update a contact")
    def update(self, request, *args, **kwargs):
        """Update a contact."""
        return super().update(request, *args, **kwargs)

    @extend_schema(description="Partially update a contact")
    def partial_update(self, request, *args, **kwargs):
        """Partially update a contact."""
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(description="Delete a contact (soft delete)")
    def destroy(self, request, *args, **kwargs):
        """Soft delete a contact."""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Bulk delete contacts",
        request=BulkDeleteSerializer,
        responses={200: {"description": "Contacts deleted successfully"}}
    )
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """Bulk delete contacts."""
        serializer = BulkDeleteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        contact_ids = serializer.validated_data['contact_ids']

        with transaction.atomic():
            contacts = Contact.objects.filter(
                id__in=contact_ids,
                organization=request.user.organization
            )
            count = contacts.count()
            for contact in contacts:
                contact.soft_delete()

        return Response({
            'message': f'{count} contacts deleted successfully',
            'deleted_count': count
        }, status=status.HTTP_200_OK)

    @extend_schema(
        description="Bulk add or remove tags from contacts",
        request=BulkTagSerializer,
        responses={200: {"description": "Tags applied successfully"}}
    )
    @action(detail=False, methods=['post'])
    def bulk_tag(self, request):
        """Bulk add or remove tags from contacts."""
        serializer = BulkTagSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        contact_ids = serializer.validated_data['contact_ids']
        tag_ids = serializer.validated_data['tag_ids']
        action_type = serializer.validated_data['action']

        contacts = Contact.objects.filter(
            id__in=contact_ids,
            organization=request.user.organization
        )
        tags = Tag.objects.filter(
            id__in=tag_ids,
            organization=request.user.organization
        )

        with transaction.atomic():
            if action_type == 'add':
                # Add tags to contacts
                for contact in contacts:
                    for tag in tags:
                        ContactTag.objects.get_or_create(
                            contact=contact,
                            tag=tag
                        )
                message = f'Tags added to {contacts.count()} contacts'
            else:
                # Remove tags from contacts
                ContactTag.objects.filter(
                    contact__in=contacts,
                    tag__in=tags
                ).delete()
                message = f'Tags removed from {contacts.count()} contacts'

        return Response({
            'message': message,
            'contact_count': contacts.count(),
            'tag_count': tags.count()
        }, status=status.HTTP_200_OK)

    @extend_schema(
        description="Export contacts to CSV",
        parameters=[
            OpenApiParameter(
                name='include_tags',
                description='Include tags in export',
                required=False,
                type=bool
            ),
        ],
        responses={200: {"description": "CSV file"}}
    )
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export contacts to CSV."""
        queryset = self.filter_queryset(self.get_queryset())
        include_tags = request.query_params.get('include_tags', 'false').lower() == 'true'

        if include_tags:
            csv_content = CSVExportService.export_contacts_with_tags(queryset)
        else:
            csv_content = CSVExportService.export_contacts(queryset)

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contacts.csv"'
        return response

    @extend_schema(
        description="Import contacts from CSV",
        request=ContactImportSerializer,
        responses={200: {"description": "Import results"}}
    )
    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        """Import contacts from CSV."""
        serializer = ContactImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        csv_file = serializer.validated_data['file']
        field_mapping = serializer.validated_data.get('field_mapping')
        skip_duplicates = serializer.validated_data.get('skip_duplicates', True)
        update_existing = serializer.validated_data.get('update_existing', False)

        # Import contacts
        import_service = CSVImportService(
            organization=request.user.organization,
            user=request.user
        )

        results = import_service.import_from_csv(
            csv_file=csv_file,
            field_mapping=field_mapping,
            skip_duplicates=skip_duplicates,
            update_existing=update_existing
        )

        return Response({
            'message': 'Import completed',
            'results': results
        }, status=status.HTTP_200_OK)

    @extend_schema(
        description="Paginated score change history for a contact.",
        responses={200: {"description": "Score history entries"}}
    )
    @action(detail=True, methods=['get'], url_path='score-history')
    def score_history(self, request, pk=None):
        """Return paginated ScoreHistory for a contact."""
        from apps.lead_scoring.models import ScoreHistory
        from apps.lead_scoring.serializers import ScoreHistorySerializer
        contact = self.get_object()
        qs = ScoreHistory.objects.filter(contact=contact).select_related('rule').order_by('-created_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ScoreHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(ScoreHistorySerializer(qs, many=True).data)

    @extend_schema(
        description="Manually adjust a contact's lead score by a signed delta.",
        responses={200: {"description": "New score"}}
    )
    @action(detail=True, methods=['post'], url_path='adjust-score')
    def adjust_score(self, request, pk=None):
        """Manually add or subtract points from a contact's lead score."""
        from apps.lead_scoring.serializers import ManualAdjustSerializer
        from apps.lead_scoring.services import LeadScoringService
        contact = self.get_object()
        serializer = ManualAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_score = LeadScoringService.manual_adjust(
            contact=contact,
            points_delta=serializer.validated_data['points_delta'],
            note=serializer.validated_data.get('note', ''),
            adjusted_by_user=request.user,
        )
        return Response({'lead_score': new_score, 'engagement_level': contact.engagement_level})

    @extend_schema(
        description="Force an immediate demographic rule recalculation for a contact.",
        responses={200: {"description": "Recalculated score"}}
    )
    @action(detail=True, methods=['post'], url_path='recalculate-score')
    def recalculate_score(self, request, pk=None):
        """Trigger a synchronous recalculation of a contact's lead score."""
        from apps.lead_scoring.services import LeadScoringService
        contact = self.get_object()
        new_score, engagement = LeadScoringService.recalculate_contact(contact)
        return Response({'lead_score': new_score, 'engagement_level': engagement})

    @extend_schema(
        description="Preview what the contact's score would be without saving.",
        responses={200: {"description": "Score preview"}}
    )
    @action(detail=True, methods=['get'], url_path='preview-score')
    def preview_score(self, request, pk=None):
        """Preview the contact's projected score without saving."""
        from apps.lead_scoring.services import LeadScoringService
        contact = self.get_object()
        return Response(LeadScoringService.preview_score(contact))

    @extend_schema(
        description="Merged, paginated activity timeline for a contact.",
        responses={200: {"description": "Timeline events"}}
    )
    @action(detail=True, methods=['get'], url_path='activity-timeline')
    def activity_timeline(self, request, pk=None):
        from .services import ActivityTimelineService
        contact = self.get_object()
        try:
            limit = min(int(request.query_params.get('limit', 20)), 100)
            offset = max(int(request.query_params.get('offset', 0)), 0)
        except (ValueError, TypeError):
            limit, offset = 20, 0
        result = ActivityTimelineService.get_timeline(contact, limit=limit, offset=offset)
        return Response(result)

    @extend_schema(
        description="Merge duplicate contacts into a primary contact.",
        responses={200: {"description": "Merged contact"}}
    )
    @action(detail=False, methods=['post'])
    def merge(self, request):
        """Merge duplicate contacts into a primary contact."""
        primary_id = request.data.get('primary_contact_id')
        duplicate_ids = request.data.get('duplicate_contact_ids', [])

        if not primary_id:
            return Response({'error': 'primary_contact_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not duplicate_ids:
            return Response({'error': 'duplicate_contact_ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        org = request.user.organization
        try:
            primary = Contact.objects.get(id=primary_id, organization=org)
        except Contact.DoesNotExist:
            return Response({'error': 'Primary contact not found'}, status=status.HTTP_404_NOT_FOUND)

        duplicates = list(Contact.objects.filter(id__in=duplicate_ids, organization=org))
        if not duplicates:
            return Response({'error': 'No valid duplicate contacts found'}, status=status.HTTP_404_NOT_FOUND)

        merged = DuplicateDetectionService.merge_contacts(primary, duplicates)
        return Response({
            'message': f'Successfully merged {len(duplicates)} contact(s) into primary',
            'contact': ContactSerializer(merged).data,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        description="Find duplicate contacts",
        responses={200: {"description": "List of duplicate groups"}}
    )
    @action(detail=False, methods=['get'])
    def duplicates(self, request):
        """Find duplicate contacts."""
        duplicate_groups = DuplicateDetectionService.find_duplicates_by_email(
            request.user.organization
        )

        # Serialize the duplicate groups
        result = []
        for group in duplicate_groups:
            serializer = ContactListSerializer(group, many=True)
            result.append({
                'email': group[0].email,
                'count': len(group),
                'contacts': serializer.data
            })

        return Response({
            'duplicate_groups': result,
            'total_groups': len(result)
        }, status=status.HTTP_200_OK)


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Tag model.

    Provides CRUD operations for tags.
    """

    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Return tags for the user's organization."""
        return Tag.objects.filter(organization=self.request.user.organization)

    def perform_create(self, serializer):
        """Set organization from the authenticated user."""
        serializer.save(organization=self.request.user.organization)

    @extend_schema(description="List all tags")
    def list(self, request, *args, **kwargs):
        """List all tags."""
        return super().list(request, *args, **kwargs)

    @extend_schema(description="Create a new tag")
    def create(self, request, *args, **kwargs):
        """Create a new tag."""
        return super().create(request, *args, **kwargs)

    @extend_schema(description="Retrieve a tag by ID")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a tag."""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(description="Update a tag")
    def update(self, request, *args, **kwargs):
        """Update a tag."""
        return super().update(request, *args, **kwargs)

    @extend_schema(description="Delete a tag")
    def destroy(self, request, *args, **kwargs):
        """Delete a tag."""
        return super().destroy(request, *args, **kwargs)


class CustomFieldViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CustomField model.

    Provides CRUD operations for custom field definitions.
    """

    serializer_class = CustomFieldSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Return custom fields for the user's organization."""
        return CustomField.objects.filter(organization=self.request.user.organization)

    def perform_create(self, serializer):
        """Set organization from the authenticated user."""
        serializer.save(organization=self.request.user.organization)

    @extend_schema(description="List all custom fields")
    def list(self, request, *args, **kwargs):
        """List all custom fields."""
        return super().list(request, *args, **kwargs)

    @extend_schema(description="Create a new custom field")
    def create(self, request, *args, **kwargs):
        """Create a new custom field."""
        return super().create(request, *args, **kwargs)

    @extend_schema(description="Retrieve a custom field by ID")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a custom field."""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(description="Update a custom field")
    def update(self, request, *args, **kwargs):
        """Update a custom field."""
        return super().update(request, *args, **kwargs)

    @extend_schema(description="Delete a custom field")
    def destroy(self, request, *args, **kwargs):
        """Delete a custom field."""
        return super().destroy(request, *args, **kwargs)
