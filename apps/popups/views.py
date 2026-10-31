import logging

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsAdminForDestructiveActions, IsOrganizationMember

from .models import Popup, PopupTemplate
from .serializers import (
    PopupCreateSerializer, PopupListSerializer, PopupSerializer,
    PopupTemplateSerializer,
)

logger = logging.getLogger(__name__)


class PopupViewSet(viewsets.ModelViewSet):
    """
    Website pop-ups.

    Actions beyond CRUD: publish, pause, duplicate.
    """
    permission_classes = [
        IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions,
    ]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'popup_type']
    search_fields = ['name', 'title']
    ordering_fields = ['created_at', 'name', 'impression_count']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            Popup.objects
            .filter(organization=self.request.user.organization, deleted_at__isnull=True)
            .select_related('form')
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return PopupListSerializer
        if self.action == 'create':
            return PopupCreateSerializer
        return PopupSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    def destroy(self, request, *args, **kwargs):
        """Soft delete, so a popup that is already live stops rather than 404s."""
        popup = self.get_object()
        popup.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Make it live, or schedule it if its start time is in the future.

        The two are the same decision to a marketer, so they are one button
        here and the status is derived rather than asked for.
        """
        from django.utils import timezone

        popup = self.get_object()
        serializer = PopupSerializer(
            popup, data={'status': Popup.STATUS_PUBLISHED}, partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)

        if popup.starts_at and popup.starts_at > timezone.now():
            popup.status = Popup.STATUS_SCHEDULED
        else:
            popup.status = Popup.STATUS_PUBLISHED
        popup.save(update_fields=['status', 'updated_at'])
        return Response(PopupSerializer(popup, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        popup = self.get_object()
        popup.status = Popup.STATUS_PAUSED
        popup.save(update_fields=['status', 'updated_at'])
        return Response(PopupSerializer(popup, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Copy it as a draft.

        Counters are deliberately not copied: a duplicate has shown to nobody,
        and inheriting another popup's conversion rate would be a lie in the
        one place a marketer goes to compare them.
        """
        original = self.get_object()
        copy = Popup.objects.create(
            organization=original.organization,
            name=f'{original.name} (copy)',
            popup_type=original.popup_type,
            status=Popup.STATUS_DRAFT,
            title=original.title,
            description=original.description,
            image_url=original.image_url,
            image_alt=original.image_alt,
            cta_text=original.cta_text,
            cta_url=original.cta_url,
            secondary_cta_text=original.secondary_cta_text,
            secondary_cta_url=original.secondary_cta_url,
            form=original.form,
            design=original.design,
            triggers=original.triggers,
            targeting=original.targeting,
            frequency=original.frequency,
            created_by=request.user,
        )
        return Response(
            PopupSerializer(copy, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class PopupTemplateViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    """System templates plus this organization's own. Read-only."""
    serializer_class = PopupTemplateSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category', 'popup_type']
    search_fields = ['name', 'description']

    def get_queryset(self):
        organization = self.request.user.organization
        return (
            PopupTemplate.objects
            .filter(is_active=True)
            .filter(Q(is_system=True) | Q(organization=organization))
        )
