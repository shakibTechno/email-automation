"""
Views for the Forms & Lead Capture app.
"""
import logging
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import Form, FormSubmission
from .serializers import (
    FormSerializer,
    FormListSerializer,
    FormCreateSerializer,
    FormUpdateSerializer,
    PublicFormSerializer,
    FormSubmissionCreateSerializer,
    FormSubmissionSerializer,
    FormSubmissionListSerializer,
)
from .filters import FormFilter
from .services import FormSubmissionService, FormExportService

logger = logging.getLogger(__name__)


class FormViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Form model.

    Provides CRUD operations and additional actions:
    - duplicate: Clone a form as inactive
    - toggle_status: Switch active/inactive
    - submissions: List form submissions
    - export_submissions: Export submissions as CSV
    - embed_code: Get HTML embed code snippet
    - share_url: Get public form URL
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = FormFilter
    search_fields = ['name']
    ordering_fields = ['name', 'status', 'submission_count', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return forms for the user's organization."""
        return Form.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related('fields', 'assign_tags')

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return FormListSerializer
        elif self.action == 'create':
            return FormCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FormUpdateSerializer
        return FormSerializer

    def perform_create(self, serializer):
        """Set organization and created_by from the authenticated user."""
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    @extend_schema(description="Soft delete a form")
    def destroy(self, request, *args, **kwargs):
        """Soft delete a form."""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Duplicate a form as inactive",
        responses={201: FormSerializer}
    )
    @action(detail=False, methods=['get'], url_path='contact-field-options')
    def contact_field_options(self, request):
        """
        What a form field may be mapped to, for the builder's dropdown.

        Served rather than hardcoded in the client: the builder's own list had
        six entries while the backend accepted every writable contact column,
        so a form could not capture anything added to the contact since that
        list was typed.
        """
        return Response({
            'options': FormSubmissionService.contact_field_options(
                request.user.organization
            ),
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Clone a form and its fields as a new inactive form."""
        original = self.get_object()

        # Generate unique name
        base_name = f"{original.name} (Copy)"
        name = base_name
        counter = 1
        while Form.objects.filter(
            organization=request.user.organization, name=name
        ).exists():
            counter += 1
            name = f"{original.name} (Copy {counter})"

        clone = Form.objects.create(
            organization=request.user.organization,
            name=name,
            description=original.description,
            status='inactive',
            form_type=original.form_type,
            submit_button_text=original.submit_button_text,
            success_message=original.success_message,
            redirect_url=original.redirect_url,
            show_gdpr_consent=original.show_gdpr_consent,
            gdpr_consent_text=original.gdpr_consent_text,
            notification_emails=original.notification_emails,
            created_by=request.user,
        )

        # Clone M2M tags
        clone.assign_tags.set(original.assign_tags.all())

        # Clone fields
        from .models import FormField
        new_fields = []
        for field in original.fields.all():
            new_fields.append(FormField(
                form=clone,
                field_type=field.field_type,
                label=field.label,
                placeholder=field.placeholder,
                help_text=field.help_text,
                is_required=field.is_required,
                options=field.options,
                validation_rules=field.validation_rules,
                order=field.order,
                contact_field_mapping=field.contact_field_mapping,
            ))
        FormField.objects.bulk_create(new_fields)

        serializer = FormSerializer(clone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        description="Toggle form status between active and inactive",
        responses={200: FormSerializer}
    )
    @action(detail=True, methods=['post'], url_path='toggle_status')
    def toggle_status(self, request, pk=None):
        """Switch form status between active and inactive."""
        form = self.get_object()
        form.status = 'inactive' if form.status == 'active' else 'active'
        form.save(update_fields=['status', 'updated_at'])

        serializer = FormSerializer(form)
        return Response(serializer.data)

    @extend_schema(
        description="List submissions for a form",
        responses={200: FormSubmissionListSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """List submissions for a form with pagination."""
        form = self.get_object()
        queryset = FormSubmission.objects.filter(
            form=form
        ).select_related('contact')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FormSubmissionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = FormSubmissionListSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Get a single submission detail",
        responses={200: FormSubmissionSerializer}
    )
    @action(detail=True, methods=['get'], url_path='submissions/(?P<submission_id>[^/.]+)')
    def submission_detail(self, request, pk=None, submission_id=None):
        """Get a single submission detail."""
        form = self.get_object()
        try:
            submission = FormSubmission.objects.select_related('contact').get(
                id=submission_id,
                form=form,
            )
        except FormSubmission.DoesNotExist:
            return Response(
                {'error': 'Submission not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = FormSubmissionSerializer(submission)
        return Response(serializer.data)

    @extend_schema(
        description="Export form submissions as CSV",
        responses={200: {"type": "string", "format": "binary"}}
    )
    @action(detail=True, methods=['get'], url_path='export_submissions')
    def export_submissions(self, request, pk=None):
        """Export all submissions for a form as a CSV file."""
        form = self.get_object()
        csv_content = FormExportService.export_submissions_csv(form)

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{form.name}_submissions.csv"'
        return response

    @extend_schema(
        description="Get embed code for a form",
        responses={200: {"type": "object"}}
    )
    @action(detail=True, methods=['get'], url_path='embed_code')
    def embed_code(self, request, pk=None):
        """Return HTML/JS embed code snippet for the form."""
        from django.conf import settings
        form = self.get_object()
        # Use frontend URL for the public form page
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        form_url = f"{frontend_url}/f/{form.id}"

        # Responsive iframe embed code
        iframe_code = (
            f'<iframe src="{form_url}" '
            f'width="100%" height="500" '
            f'frameborder="0" '
            f'style="border:none; max-width:100%;" '
            f'title="{form.name}">'
            f'</iframe>'
        )

        # Simple div + script embed (loads form in a container)
        embed_html = (
            f'<div id="em-form-{form.id}" style="max-width:500px;margin:0 auto;"></div>\n'
            f'<script>\n'
            f'(function(){{\n'
            f'  var container = document.getElementById("em-form-{form.id}");\n'
            f'  var iframe = document.createElement("iframe");\n'
            f'  iframe.src = "{form_url}";\n'
            f'  iframe.style.cssText = "width:100%;height:500px;border:none;";\n'
            f'  iframe.title = "{form.name}";\n'
            f'  container.appendChild(iframe);\n'
            f'}})();\n'
            f'</script>'
        )

        return Response({
            'embed_html': embed_html,
            'iframe_code': iframe_code,
            'form_url': form_url,
        })

    @extend_schema(
        description="Get the public share URL for a form",
        responses={200: {"type": "object"}}
    )
    @action(detail=True, methods=['get'], url_path='share_url')
    def share_url(self, request, pk=None):
        """Return the public share URL for the form."""
        from django.conf import settings
        form = self.get_object()
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        form_url = f"{frontend_url}/f/{form.id}"
        return Response({
            'url': form_url,
        })


class PublicFormViewSet(viewsets.GenericViewSet):
    """
    ViewSet for public (unauthenticated) form access and submission.
    """
    permission_classes = [AllowAny]
    queryset = Form.objects.filter(status='active')
    serializer_class = PublicFormSerializer

    def get_queryset(self):
        return Form.objects.filter(status='active').prefetch_related('fields')

    @extend_schema(
        description="Get public form structure for rendering",
        responses={200: PublicFormSerializer}
    )
    def retrieve(self, request, pk=None):
        """Get form structure for public rendering (only active forms)."""
        try:
            form = self.get_queryset().get(pk=pk)
        except Form.DoesNotExist:
            return Response(
                {'error': 'Form not found or inactive.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PublicFormSerializer(form)
        return Response(serializer.data)

    @extend_schema(
        description="Submit a public form",
        request=FormSubmissionCreateSerializer,
        responses={201: {"type": "object"}}
    )
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Process a public form submission."""
        try:
            form = self.get_queryset().get(pk=pk)
        except Form.DoesNotExist:
            return Response(
                {'error': 'Form not found or inactive.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = FormSubmissionCreateSerializer(
            data=request.data,
            context={'form': form}
        )
        serializer.is_valid(raise_exception=True)

        # Get client info
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        submission = FormSubmissionService.process_submission(
            form=form,
            data=serializer.validated_data['data'],
            ip_address=ip_address,
            user_agent=user_agent,
            source_url=serializer.validated_data.get('source_url', ''),
        )

        # Link this browser's earlier visits to the contact the service just
        # resolved from the submitted email. Server-side on purpose: the
        # client supplies only an opaque visitor id, never a contact.
        visitor_key = serializer.validated_data.get('visitor_id', '')
        if visitor_key and submission.contact_id:
            try:
                from apps.tracking.services import identify
                identify(form.organization, visitor_key, submission.contact)
            except Exception:
                # A submission must never fail because tracking did.
                logger.exception('Could not identify visitor %s', visitor_key)

        # Update GDPR consent on submission
        if serializer.validated_data.get('gdpr_consent_given'):
            submission.gdpr_consent_given = True
            submission.save(update_fields=['gdpr_consent_given'])

        # A form embedded in a landing page is submitted from a URL carrying
        # that page's id, which is what makes the page's conversion figure
        # real rather than decorative. Best-effort by design: a submission the
        # visitor completed must never fail over attribution bookkeeping.
        try:
            from apps.landing_pages.services import LandingPageService
            LandingPageService.record_form_conversion(
                organization=form.organization,
                source_url=serializer.validated_data.get('source_url', ''),
            )
        except Exception:
            logger.exception('Failed to record landing page conversion')

        # Notify org admins of new submission
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_org_admins(
                organization=form.organization,
                notification_type='form_submission',
                title='New form submission',
                message=f'Someone submitted "{form.name}".',
                data={'form_id': str(form.id), 'submission_id': str(submission.id)},
            )
        except Exception:
            pass

        return Response(
            {
                'message': form.success_message,
                'redirect_url': form.redirect_url or None,
                'submission_id': str(submission.id),
            },
            status=status.HTTP_201_CREATED
        )

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
