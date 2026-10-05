"""
Views for the Email Templates app.
"""
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import EmailTemplate, TemplateImage
from .serializers import (
    EmailTemplateSerializer,
    EmailTemplateListSerializer,
    EmailTemplateCreateSerializer,
    EmailTemplateUpdateSerializer,
    TemplateImageSerializer,
)
from .filters import EmailTemplateFilter
import logging

logger = logging.getLogger(__name__)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for EmailTemplate model.

    Provides CRUD operations and additional actions:
    - duplicate: Clone an existing template
    - export_html: Export HTML from a template
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EmailTemplateFilter
    search_fields = ['name', 'description', 'subject']
    ordering_fields = ['name', 'category', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return templates for the user's organization."""
        return EmailTemplate.objects.filter(
            organization=self.request.user.organization
        )

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return EmailTemplateListSerializer
        elif self.action == 'create':
            return EmailTemplateCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EmailTemplateUpdateSerializer
        return EmailTemplateSerializer

    def perform_create(self, serializer):
        """Set organization from the authenticated user."""
        serializer.save(organization=self.request.user.organization)

    @extend_schema(description="Soft delete a template")
    def destroy(self, request, *args, **kwargs):
        """Soft delete a template."""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Duplicate an existing template",
        responses={201: EmailTemplateSerializer}
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Clone a template."""
        original = self.get_object()

        # Generate unique name
        base_name = f"{original.name} (Copy)"
        name = base_name
        counter = 1
        while EmailTemplate.objects.filter(
            organization=request.user.organization, name=name
        ).exists():
            counter += 1
            name = f"{original.name} (Copy {counter})"

        clone = EmailTemplate.objects.create(
            organization=request.user.organization,
            name=name,
            description=original.description,
            category=original.category,
            subject=original.subject,
            design_json=original.design_json,
            html_content=original.html_content,
            thumbnail_url=original.thumbnail_url,
            is_preset=False,
        )

        serializer = EmailTemplateSerializer(clone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        description="Export HTML content from a template",
        responses={200: {"type": "object", "properties": {"html": {"type": "string"}}}}
    )
    @action(detail=True, methods=['post'])
    def export_html(self, request, pk=None):
        """Export HTML from a template's design."""
        template = self.get_object()
        return Response({
            'html': template.html_content,
            'subject': template.subject,
        }, status=status.HTTP_200_OK)


class TemplateImageViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet for TemplateImage model.

    Provides create (upload), list, and delete operations.
    """

    serializer_class = TemplateImageSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Return images for the user's organization."""
        return TemplateImage.objects.filter(
            organization=self.request.user.organization
        )

    def perform_create(self, serializer):
        """Set organization and extract file metadata."""
        image_file = self.request.FILES.get('image')
        if not image_file:
            return

        # Extract metadata
        original_filename = image_file.name
        file_size = image_file.size

        # Try to get image dimensions
        width = None
        height = None
        try:
            from PIL import Image
            img = Image.open(image_file)
            width, height = img.size
            image_file.seek(0)  # Reset file pointer after reading
        except Exception:
            pass

        serializer.save(
            organization=self.request.user.organization,
            original_filename=original_filename,
            file_size=file_size,
            width=width,
            height=height,
        )
