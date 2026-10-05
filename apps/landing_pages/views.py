"""
Views for the Landing Pages app.
"""
import logging
import mimetypes
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import LandingPage, LandingPageTemplate, LandingPageAsset
from .serializers import (
    LandingPageSerializer,
    LandingPageListSerializer,
    LandingPageCreateSerializer,
    LandingPageUpdateSerializer,
    LandingPageDesignSerializer,
    PublicLandingPageSerializer,
    LandingPageTemplateSerializer,
    LandingPageTemplateDetailSerializer,
    SaveAsTemplateSerializer,
    LandingPageAssetSerializer,
    PageAnalyticsSerializer,
)
from .filters import LandingPageFilter, LandingPageTemplateFilter
from .services import LandingPageService, LandingPageAnalyticsService, LandingPageTemplateService

logger = logging.getLogger(__name__)


class LandingPageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LandingPage model.

    Provides CRUD operations and additional actions:
    - publish: Publish a landing page
    - unpublish: Unpublish a landing page
    - duplicate: Clone a landing page
    - save_design: Auto-save GrapesJS design
    - preview: Get preview HTML
    - analytics: Get page analytics
    - upload_asset: Upload image/video asset
    - assets: List page assets
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LandingPageFilter
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'status', 'view_count', 'published_at', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return landing pages for the user's organization."""
        return LandingPage.objects.filter(
            organization=self.request.user.organization
        ).select_related('form', 'created_by')

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return LandingPageListSerializer
        elif self.action == 'create':
            return LandingPageCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return LandingPageUpdateSerializer
        elif self.action == 'save_design':
            return LandingPageDesignSerializer
        return LandingPageSerializer

    def perform_create(self, serializer):
        """Create is handled by serializer which sets organization and created_by."""
        serializer.save()

    @extend_schema(description="Soft delete a landing page")
    def destroy(self, request, *args, **kwargs):
        """Soft delete a landing page."""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Publish a landing page",
        responses={200: LandingPageSerializer}
    )
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a landing page."""
        landing_page = self.get_object()
        try:
            landing_page = LandingPageService.publish_page(landing_page)
            serializer = LandingPageSerializer(landing_page)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        description="Unpublish a landing page",
        responses={200: LandingPageSerializer}
    )
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish a landing page."""
        landing_page = self.get_object()
        landing_page = LandingPageService.unpublish_page(landing_page)
        serializer = LandingPageSerializer(landing_page)
        return Response(serializer.data)

    @extend_schema(
        description="Duplicate a landing page",
        responses={201: LandingPageSerializer}
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Clone a landing page as a new draft."""
        landing_page = self.get_object()
        clone = LandingPageService.duplicate_page(landing_page, request.user)
        serializer = LandingPageSerializer(clone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        description="Save GrapesJS design (auto-save)",
        request=LandingPageDesignSerializer,
        responses={200: LandingPageSerializer}
    )
    @action(detail=True, methods=['patch'], url_path='save_design')
    def save_design(self, request, pk=None):
        """Save GrapesJS design data."""
        landing_page = self.get_object()
        serializer = LandingPageDesignSerializer(
            landing_page,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LandingPageSerializer(landing_page).data)

    @extend_schema(
        description="Get preview HTML for a landing page",
        responses={200: {"type": "object"}}
    )
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Get preview HTML for the landing page."""
        landing_page = self.get_object()
        html = LandingPageService.render_page_html(landing_page)
        return Response({'html': html})

    @extend_schema(
        description="Get analytics for a landing page",
        responses={200: PageAnalyticsSerializer}
    )
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics data for a landing page."""
        landing_page = self.get_object()
        days = int(request.query_params.get('days', 30))
        analytics = LandingPageAnalyticsService.get_page_analytics(landing_page, days)
        serializer = PageAnalyticsSerializer(analytics)
        return Response(serializer.data)

    @extend_schema(
        description="Upload an asset for the landing page",
        request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}},
        responses={201: LandingPageAssetSerializer}
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='upload_asset',
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload_asset(self, request, pk=None):
        """Upload an image or video asset for the landing page."""
        landing_page = self.get_object()
        file = request.FILES.get('file')

        if not file:
            return Response(
                {'error': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine file type
        mime_type = file.content_type or mimetypes.guess_type(file.name)[0] or ''
        if mime_type.startswith('image/'):
            file_type = 'image'
        elif mime_type.startswith('video/'):
            file_type = 'video'
        else:
            file_type = 'document'

        asset = LandingPageAsset.objects.create(
            organization=request.user.organization,
            landing_page=landing_page,
            file=file,
            file_type=file_type,
            file_name=file.name,
            file_size=file.size,
            mime_type=mime_type,
        )

        serializer = LandingPageAssetSerializer(asset)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        description="List assets for a landing page",
        responses={200: LandingPageAssetSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def assets(self, request, pk=None):
        """List all assets for a landing page."""
        landing_page = self.get_object()
        assets = LandingPageAsset.objects.filter(landing_page=landing_page)
        serializer = LandingPageAssetSerializer(assets, many=True)
        return Response(serializer.data)


class LandingPageTemplateViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet for LandingPageTemplate model.

    Provides list and retrieve operations, plus:
    - save_as_template: Save a landing page as a template
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = LandingPageTemplateFilter
    search_fields = ['name', 'description']
    ordering = ['-usage_count', '-created_at']

    def get_queryset(self):
        """Return system templates and user's organization templates."""
        org = self.request.user.organization
        return LandingPageTemplate.objects.filter(
            is_active=True
        ).filter(
            models.Q(is_system=True) | models.Q(organization=org)
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LandingPageTemplateDetailSerializer
        return LandingPageTemplateSerializer

    @extend_schema(
        description="Save a landing page as a reusable template",
        request=SaveAsTemplateSerializer,
        responses={201: LandingPageTemplateSerializer}
    )
    @action(detail=False, methods=['post'], url_path='save_as_template')
    def save_as_template(self, request):
        """Save a landing page as a template."""
        serializer = SaveAsTemplateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        landing_page = LandingPage.objects.get(
            id=serializer.validated_data['landing_page_id']
        )

        template = LandingPageTemplateService.save_as_template(
            landing_page=landing_page,
            name=serializer.validated_data['name'],
            category=serializer.validated_data['category'],
            description=serializer.validated_data.get('description', '')
        )

        return Response(
            LandingPageTemplateSerializer(template).data,
            status=status.HTTP_201_CREATED
        )


# Import models at module level for the Q filter
from django.db import models


class PublicLandingPageView(APIView):
    """
    View for rendering public landing pages.

    GET /p/{slug}/ - Render published landing page
    """

    permission_classes = [AllowAny]

    def get(self, request, slug):
        """Render a published landing page."""
        try:
            landing_page = LandingPage.objects.get(
                slug=slug,
                status='published'
            )
        except LandingPage.DoesNotExist:
            return HttpResponse(
                '<html><body><h1>Page Not Found</h1></body></html>',
                status=404,
                content_type='text/html'
            )

        # Record page view
        LandingPageAnalyticsService.record_page_view(landing_page, request)

        # Render and return HTML
        html = LandingPageService.render_page_html(landing_page)
        return HttpResponse(html, content_type='text/html')
