"""
API views for the AI Assistant app.
"""
import logging

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOrganizationAdmin, IsOrganizationMember

from .models import GenerationJob
from .serializers import (
    AIConfigurationSerializer,
    AIConfigurationUpdateSerializer,
    GenerationJobSerializer,
    GenerationRequestSerializer,
)
from .services import AIConfigService
from .tasks import run_generation

logger = logging.getLogger(__name__)


class AIConfigView(APIView):
    """Read or update the organization's AI connection."""

    # An API key is a billing-bearing credential, so only admins may set one;
    # any member may read whether the feature is available to them.
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAuthenticated(), IsOrganizationMember(), IsOrganizationAdmin()]
        return super().get_permissions()

    @extend_schema(responses={200: AIConfigurationSerializer})
    def get(self, request):
        config = AIConfigService.get_or_create(request.user.organization)
        return Response(AIConfigurationSerializer(config).data)

    @extend_schema(
        request=AIConfigurationUpdateSerializer,
        responses={200: AIConfigurationSerializer},
    )
    def patch(self, request):
        config = AIConfigService.get_or_create(request.user.organization)
        serializer = AIConfigurationUpdateSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        config = serializer.save()
        return Response(AIConfigurationSerializer(config).data)

    put = patch


class AIConfigTestView(APIView):
    """Check the saved credentials against the provider."""

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsOrganizationAdmin]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        config = AIConfigService.get_or_create(request.user.organization)
        ok, message = AIConfigService.test_connection(config)
        return Response(
            {'success': ok, 'message': message,
             'config': AIConfigurationSerializer(config).data},
            status=status.HTTP_200_OK if ok else status.HTTP_400_BAD_REQUEST,
        )


class GenerateView(APIView):
    """
    Queue a generation.

    One endpoint for every kind: the URL carries what to build, so adding a
    kind needs no new view.
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    VALID_KINDS = {kind for kind, _ in GenerationJob.KIND_CHOICES}

    @extend_schema(
        request=GenerationRequestSerializer,
        responses={202: GenerationJobSerializer},
    )
    def post(self, request, kind):
        if kind not in self.VALID_KINDS:
            return Response(
                {'error': f'Cannot generate "{kind}".'},
                status=status.HTTP_404_NOT_FOUND,
            )

        config = AIConfigService.get_or_create(request.user.organization)
        if not config.is_ready:
            return Response(
                {'error': 'No AI provider is connected. Add a key in Settings → AI.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = GenerationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = GenerationJob.objects.create(
            organization=request.user.organization,
            created_by=request.user,
            kind=kind,
            prompt=serializer.validated_data['prompt'],
            audience=serializer.validated_data.get('audience', ''),
        )
        run_generation.delay(str(job.id))

        return Response(
            GenerationJobSerializer(job).data,
            status=status.HTTP_202_ACCEPTED,
        )


class GenerationJobView(APIView):
    """Poll one generation job."""

    permission_classes = [IsAuthenticated, IsOrganizationMember]

    @extend_schema(responses={200: GenerationJobSerializer})
    def get(self, request, job_id):
        try:
            job = GenerationJob.objects.get(
                pk=job_id, organization=request.user.organization,
            )
        except (GenerationJob.DoesNotExist, ValueError, ValidationError):
            return Response(
                {'error': 'Generation not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(GenerationJobSerializer(job).data)
