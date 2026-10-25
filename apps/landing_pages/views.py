"""
Views for the Landing Pages app.
"""
import logging
import mimetypes
import secrets
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework import viewsets, status, mixins, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from apps.core.viewsets import OrganizationScopedQuerysetMixin
from .domain_service import DomainError, LandingDomainService
from .permissions import CustomDomainsEnabled
from .models import LandingDomain, LandingPage, LandingPageTemplate, LandingPageAsset
from .serializers import (
    LandingDomainSerializer,
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


class IsOrganizationMemberOrSystemTemplate(IsOrganizationMember):
    """
    Object permission for templates, which are either an organization's own or
    shared across all of them.

    `IsOrganizationMember` answers `obj.organization == request.user.organization`,
    and a system template's organization is None — so every built-in template
    listed fine but 403'd the moment anything tried to open one. The queryset
    already restricts the set to system templates plus the caller's own, so
    there is nothing for the object check to add beyond letting the shared ones
    through.
    """

    def has_object_permission(self, request, view, obj):
        if getattr(obj, 'is_system', False):
            return True
        return super().has_object_permission(request, view, obj)


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

    permission_classes = [
        IsAuthenticated,
        IsOrganizationMemberOrSystemTemplate,
        IsAdminForDestructiveActions,
    ]
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


class DomainVerificationTokenView(APIView):
    """
    Echoes a connected domain's verification token.

    Reachable only on the customer's own hostname (see `config.urls_landing`),
    which is the whole point: if we can serve this and then read it back over
    `https://<their domain>/...`, their DNS points here *and* the certificate
    works. A DNS lookup proves neither — a CNAME chain or a proxy in front can
    satisfy a resolver and still not deliver traffic to us.
    """

    permission_classes = [AllowAny]

    def get(self, request, token):
        row = getattr(request, 'landing_domain', None)
        if not row:
            return HttpResponse(status=404)
        # Compared against this host's own token only, so holding one domain's
        # token says nothing about any other.
        expected = LandingDomain.objects.filter(pk=row['id']).values_list(
            'verification_token', flat=True
        ).first()
        if not expected or not secrets.compare_digest(str(token), str(expected)):
            return HttpResponse(status=404)
        return HttpResponse(expected, content_type='text/plain')


class PublicLandingPageView(APIView):
    """
    View for rendering public landing pages.

    GET https://<connected domain>/          - that domain's home page
    GET https://<connected domain>/{slug}/   - a page on that domain
    GET /p/{org_slug}/{slug}/                - the platform address
    GET /p/{slug}/                           - Legacy, unscoped form (see below)

    Page slugs are unique per organization, not globally
    (`LandingPage.Meta.unique_together`). The unscoped form therefore cannot
    identify a page on its own: two tenants publishing "pricing" or
    "black-friday" is not a corner case, it is the expected case. It is kept
    only so links already in the wild keep resolving, and it refuses to guess.
    A connected domain has no such problem — the hostname names the tenant.
    """

    permission_classes = [AllowAny]

    NOT_FOUND_HTML = '<html><body><h1>Page Not Found</h1></body></html>'

    def _not_found(self):
        return HttpResponse(self.NOT_FOUND_HTML, status=404, content_type='text/html')

    def get(self, request, slug=None, org_slug=None):
        """Render a published landing page."""
        landing_domain = getattr(request, 'landing_domain', None)

        if landing_domain is not None:
            # On a connected domain the organization comes from the hostname,
            # never from the URL, so one tenant's domain cannot be pointed at
            # another tenant's page.
            return self._serve_on_domain(request, landing_domain, slug)

        if slug is None:
            return self._not_found()

        pages = LandingPage.objects.select_related('organization').filter(
            slug=slug,
            status='published',
        )

        if org_slug is not None:
            landing_page = pages.filter(organization__slug=org_slug).first()
            if landing_page is None:
                return self._not_found()
        else:
            # Deliberately not `.get()`: that raised MultipleObjectsReturned and
            # returned a 500 as soon as any two tenants shared a slug. An
            # ambiguous link is answered with the same 404 a missing one gets —
            # a visitor must not be served another tenant's page, and must not
            # learn from the response that other tenants exist.
            matches = list(pages[:2])
            if len(matches) != 1:
                if matches:
                    logger.warning(
                        "Ambiguous unscoped landing page slug %r matches multiple "
                        "organizations; the org-scoped URL is required.", slug,
                    )
                return self._not_found()
            landing_page = matches[0]

        return self._render(request, landing_page)

    def _serve_on_domain(self, request, landing_domain, slug):
        """Resolve a page within the organization that owns this hostname."""
        pages = LandingPage.objects.select_related('organization', 'domain').filter(
            organization_id=landing_domain['organization_id'],
            status='published',
        )

        # A page pinned to another of the organization's domains does not belong
        # on this one, but an unpinned page follows the primary domain.
        pages = pages.filter(
            models.Q(domain_id=landing_domain['id'])
            | models.Q(domain_id__isnull=True)
        )

        if slug is None:
            landing_page = pages.filter(is_domain_home=True).first()
        else:
            landing_page = pages.filter(slug=slug).first()

        if landing_page is None:
            return self._not_found()
        return self._render(request, landing_page)

    def _render(self, request, landing_page):
        # Record page view
        LandingPageAnalyticsService.record_page_view(landing_page, request)

        # Render and return HTML
        html = LandingPageService.render_page_html(landing_page)
        return HttpResponse(html, content_type='text/html')


class LandingDomainViewSet(
    OrganizationScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    The domains an organization has connected for its landing pages.

    No update route: a domain's name is its identity, and renaming one would
    silently move every page served from it. Change it by disconnecting and
    connecting the new name, which makes the DNS step unavoidable — as it
    should be.
    """

    serializer_class = LandingDomainSerializer
    queryset = LandingDomain.objects.all()
    permission_classes = [
        IsAuthenticated,
        IsOrganizationMember,
        CustomDomainsEnabled,
        IsAdminForDestructiveActions,
    ]

    def get_queryset(self):
        # order_by restated: annotate() clears Meta.ordering, and an unordered
        # queryset makes paginated results shuffle between pages.
        return (
            super().get_queryset()
            .annotate(page_count=Count('pages'))
            .order_by('-is_primary', 'domain')
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            domain = LandingDomainService.connect(
                request.user.organization, serializer.validated_data['domain'],
            )
        except DomainError as exc:
            raise serializers.ValidationError({'domain': str(exc)})
        return Response(
            self.get_serializer(domain).data, status=status.HTTP_201_CREATED,
        )

    def perform_destroy(self, instance):
        LandingDomainService.disconnect(instance)

    @extend_schema(request=None, responses={200: LandingDomainSerializer})
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """
        Check the domain now.

        Always 200, including when verification fails: "your DNS is not ready"
        is an answer, not an error, and the detail the customer needs is in
        `last_check_error` either way.
        """
        domain = LandingDomainService.verify(self.get_object())
        return Response(self.get_serializer(domain).data)

    @extend_schema(request=None, responses={200: LandingDomainSerializer})
    @action(detail=True, methods=['post'], url_path='set-primary')
    def set_primary(self, request, pk=None):
        """Make this the domain that unpinned pages are served from."""
        domain = LandingDomainService.set_primary(self.get_object())
        return Response(self.get_serializer(domain).data)
