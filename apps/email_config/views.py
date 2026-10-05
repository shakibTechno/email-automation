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

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import EmailConfiguration, SendingDomain
from .serializers import (
    EmailConfigSerializer,
    EmailConfigUpdateSerializer,
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
    """POST /api/v1/email-config/resume/ — clear the threshold-pause flag"""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def post(self, request):
        config = EmailConfigService.get_or_create(request.user.organization)
        config.sending_paused_due_to_threshold = False
        config.save(update_fields=['sending_paused_due_to_threshold'])
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

    def perform_create(self, serializer):
        org = self.request.user.organization
        domain = serializer.validated_data['domain'].lower().strip()

        # Generate DNS records
        records = EmailConfigService.generate_dns_records(domain)
        serializer.save(
            organization=org,
            domain=domain,
            spf_record=records['spf_record'],
            dkim_selector=records['dkim_selector'],
            dkim_record_name=records['dkim_record_name'],
            dkim_record_value=records['dkim_record_value'],
        )

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        sending_domain = self.get_object()
        success, message = EmailConfigService.verify_domain(sending_domain)
        return Response({
            'success': success,
            'message': message,
            'status': sending_domain.status,
            'verified_at': sending_domain.verified_at,
        }, status=200 if success else 400)
