"""
Views for email configuration.
"""
import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import viewsets

from apps.core.permissions import (
    IsOrganizationMember,
    IsOrganizationAdmin,
    IsAdminForDestructiveActions,
)
from .models import SendingDomain
from .provisioner_client import ProvisionerError
from .provisioning import PostalProvisioningService
from .serializers import (
    EmailConfigSerializer,
    EmailConfigUpdateSerializer,
    PostalTenantSerializer,
    SendingDomainSerializer,
    SendingDomainCreateSerializer,
)
from .services import EmailConfigService

logger = logging.getLogger(__name__)


class EmailConfigView(APIView):
    """
    GET  /api/v1/email-config/   — retrieve org config (creates defaults if absent)
    PUT  /api/v1/email-config/   — update config
    POST /api/v1/email-config/test/ — send test email
    POST /api/v1/email-config/resume/ — clear threshold pause flag
    """
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        config = EmailConfigService.get_or_create(request.user.organization)
        return Response(EmailConfigSerializer(config).data)

    def put(self, request):
        config = EmailConfigService.get_or_create(request.user.organization)
        serializer = EmailConfigUpdateSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EmailConfigSerializer(config).data)

    def patch(self, request):
        return self.put(request)


class EmailConfigTestView(APIView):
    """POST /api/v1/email-config/test/"""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def post(self, request):
        to_email = request.data.get('to_email') or request.user.email
        success, message = EmailConfigService.test_connection(
            request.user.organization, to_email
        )
        if success:
            return Response({'success': True, 'message': message})
        return Response({'success': False, 'message': message}, status=400)


class EmailConfigResumeView(APIView):
    """
    POST /api/v1/email-config/resume/ — resume sending after a threshold pause.

    Clears the local pause flag and, if the guardrails also suspended the
    organization's Postal tenant, lifts that too. Without the second step mail
    would stay held in Postal while the UI showed sending as resumed.

    Admin-only: resuming after a bounce or complaint breach is a decision that
    affects the shared sending IP.
    """
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsOrganizationAdmin]

    def post(self, request):
        org = request.user.organization
        config = EmailConfigService.get_or_create(org)
        config.sending_paused_due_to_threshold = False
        config.save(update_fields=['sending_paused_due_to_threshold'])

        tenant = PostalProvisioningService.get_tenant(org)
        if tenant and tenant.is_suspended:
            try:
                PostalProvisioningService.unsuspend(tenant)
            except ProvisionerError as exc:
                logger.warning('Could not unsuspend tenant for org %s: %s', org.id, exc)
                return Response({
                    'resumed': True,
                    'warning': (
                        'Sending was resumed locally, but the mail server is still '
                        f'suspended: {exc.message or exc}'
                    ),
                })
        return Response({'resumed': True})


class SendingDomainViewSet(viewsets.ModelViewSet):
    """
    /api/v1/email-config/domains/
    """
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]

    def get_queryset(self):
        return SendingDomain.objects.filter(organization=self.request.user.organization)

    def get_serializer_class(self):
        if self.action == 'create':
            return SendingDomainCreateSerializer
        return SendingDomainSerializer

    def create(self, request, *args, **kwargs):
        """
        Register a sending domain with the platform mail server.

        This is the lazy provisioning trigger: the organization's Postal mail
        server is created here, on the first domain, rather than at signup.
        The provisioner generates the real DKIM key and returns the records to
        publish, so nothing is written locally until it has answered.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        domain_name = serializer.validated_data['domain'].lower().strip().rstrip('.')
        org = request.user.organization

        if SendingDomain.objects.filter(organization=org, domain=domain_name).exists():
            return Response(
                {'detail': f'{domain_name} is already added.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            domain = PostalProvisioningService.add_domain(org, domain_name)
        except ProvisionerError as exc:
            logger.warning('Adding domain %s for org %s failed: %s', domain_name, org.id, exc)
            return Response(
                {'detail': exc.message or str(exc), 'code': exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            SendingDomainSerializer(domain).data, status=status.HTTP_201_CREATED
        )

    def perform_destroy(self, instance):
        """Remove the domain from Postal before dropping the local mirror."""
        try:
            PostalProvisioningService.delete_domain(instance)
        except ProvisionerError as exc:
            # Don't strand the row locally if the remote call fails; log and
            # continue, since a leftover Postal domain can be cleaned up there.
            logger.warning(
                'Could not remove domain %s from Postal: %s', instance.domain, exc
            )
        instance.delete()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        sending_domain = self.get_object()
        success, message = EmailConfigService.verify_domain(sending_domain)
        sending_domain.refresh_from_db()
        return Response({
            'success': success,
            'message': message,
            'status': sending_domain.status,
            'sending_enabled': sending_domain.sending_enabled,
            'verified_at': sending_domain.verified_at,
            'dns_records': sending_domain.dns_records,
        }, status=200 if success else 400)


class PostalTenantView(APIView):
    """
    GET /api/v1/email-config/tenant/ — the organization's mail server status.

    Returns null when the organization has no tenant yet, which is the normal
    state until someone adds a sending domain.
    """
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        tenant = PostalProvisioningService.get_tenant(request.user.organization)
        if not tenant:
            return Response({'tenant': None})
        return Response({'tenant': PostalTenantSerializer(tenant).data})


class PostalTenantSyncView(APIView):
    """POST /api/v1/email-config/tenant/sync/ — refresh cached Postal metrics."""
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsOrganizationAdmin]

    def post(self, request):
        tenant = PostalProvisioningService.get_tenant(request.user.organization)
        if not tenant:
            return Response(
                {'detail': 'This organization has no mail server yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            PostalProvisioningService.sync_tenant(tenant)
        except ProvisionerError as exc:
            return Response(
                {'detail': exc.message or str(exc), 'code': exc.code},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({'tenant': PostalTenantSerializer(tenant).data})
