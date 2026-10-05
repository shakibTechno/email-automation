"""
Views for the integrations app.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOrganizationMember, IsOrganizationAdmin
from .models import SocialIntegration
from .serializers import (
    AnalyticsIntegrationSerializer,
    UpsertAnalyticsSerializer,
    SocialIntegrationSerializer,
    UpdateSocialIntegrationSerializer,
    UpdateCredentialsSerializer,
    LeadSyncLogSerializer,
    DemoConnectSerializer,
)
from .services import (
    AnalyticsIntegrationService,
    SocialIntegrationService,
    LeadImportService,
)


# --------------------------------------------------------------------------
# Analytics Integration views
# --------------------------------------------------------------------------

class AnalyticsIntegrationListView(APIView):
    """List all analytics integrations for the current organization."""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        integrations = AnalyticsIntegrationService.get_integrations(
            request.user.organization
        )
        serializer = AnalyticsIntegrationSerializer(integrations, many=True)
        return Response(serializer.data)


class AnalyticsIntegrationUpsertView(APIView):
    """Create or update an analytics integration."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        serializer = UpsertAnalyticsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        integration = AnalyticsIntegrationService.upsert_integration(
            organization=request.user.organization,
            provider=data['provider'],
            tracking_id=data['tracking_id'],
            is_enabled=data.get('is_enabled', True),
            settings=data.get('settings'),
        )
        return Response(
            AnalyticsIntegrationSerializer(integration).data,
            status=status.HTTP_200_OK,
        )


class AnalyticsIntegrationDeleteView(APIView):
    """Delete an analytics integration by provider."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def delete(self, request, provider):
        deleted = AnalyticsIntegrationService.delete_integration(
            request.user.organization, provider
        )
        if not deleted:
            return Response(
                {'detail': 'Integration not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# Social Integration views
# --------------------------------------------------------------------------

class SocialIntegrationListView(APIView):
    """List all social integrations for the current organization."""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        integrations = SocialIntegrationService.get_integrations(
            request.user.organization
        )
        serializer = SocialIntegrationSerializer(integrations, many=True)
        return Response(serializer.data)


class SocialIntegrationUpdateView(APIView):
    """Update settings for a social integration."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def patch(self, request, pk):
        try:
            integration = SocialIntegration.objects.get(
                id=pk, organization=request.user.organization
            )
        except SocialIntegration.DoesNotExist:
            return Response(
                {'detail': 'Integration not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateSocialIntegrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        integration = SocialIntegrationService.update_settings(
            integration, serializer.validated_data
        )
        return Response(SocialIntegrationSerializer(integration).data)


class SocialIntegrationDisconnectView(APIView):
    """Disconnect a social integration."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, pk):
        try:
            integration = SocialIntegration.objects.get(
                id=pk, organization=request.user.organization
            )
        except SocialIntegration.DoesNotExist:
            return Response(
                {'detail': 'Integration not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = SocialIntegrationService.disconnect(
            request.user.organization, integration.platform
        )
        return Response(SocialIntegrationSerializer(result).data)


class SocialIntegrationSyncView(APIView):
    """Trigger a lead sync for a social integration."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, pk):
        try:
            integration = SocialIntegration.objects.get(
                id=pk, organization=request.user.organization
            )
        except SocialIntegration.DoesNotExist:
            return Response(
                {'detail': 'Integration not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if integration.status != 'connected':
            return Response(
                {'detail': 'Integration is not connected'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sync_log = LeadImportService.import_leads(integration)
        return Response(
            LeadSyncLogSerializer(sync_log).data,
            status=status.HTTP_200_OK,
        )


class SyncHistoryView(APIView):
    """List sync history for a social integration."""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request, pk):
        try:
            integration = SocialIntegration.objects.get(
                id=pk, organization=request.user.organization
            )
        except SocialIntegration.DoesNotExist:
            return Response(
                {'detail': 'Integration not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        sync_logs = integration.sync_logs.order_by('-created_at')[:20]
        serializer = LeadSyncLogSerializer(sync_logs, many=True)
        return Response(serializer.data)


class DemoConnectView(APIView):
    """Connect a social integration in demo mode."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        serializer = DemoConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        integration = SocialIntegrationService.demo_connect(
            organization=request.user.organization,
            platform=serializer.validated_data['platform'],
            user=request.user,
        )
        return Response(
            SocialIntegrationSerializer(integration).data,
            status=status.HTTP_200_OK,
        )


class SocialIntegrationUpdateCredentialsView(APIView):
    """Save API credentials for a social integration."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, pk):
        try:
            integration = SocialIntegration.objects.get(
                id=pk, organization=request.user.organization
            )
        except SocialIntegration.DoesNotExist:
            return Response(
                {'detail': 'Integration not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateCredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        integration = SocialIntegrationService.update_credentials(
            integration, serializer.validated_data
        )
        return Response(SocialIntegrationSerializer(integration).data)


class SocialIntegrationConnectView(APIView):
    """Connect a social integration using stored API credentials."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, pk):
        try:
            integration = SocialIntegration.objects.get(
                id=pk, organization=request.user.organization
            )
        except SocialIntegration.DoesNotExist:
            return Response(
                {'detail': 'Integration not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            result = SocialIntegrationService.connect(
                organization=request.user.organization,
                platform=integration.platform,
                user=request.user,
            )
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(SocialIntegrationSerializer(result).data)


class FieldMappingOptionsView(APIView):
    """Return available Contact fields for field mapping configuration."""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        options = [
            {'value': 'email', 'label': 'Email'},
            {'value': 'first_name', 'label': 'First Name'},
            {'value': 'last_name', 'label': 'Last Name'},
            {'value': 'phone', 'label': 'Phone'},
            {'value': 'company', 'label': 'Company'},
            {'value': 'job_title', 'label': 'Job Title'},
        ]
        return Response(options)
