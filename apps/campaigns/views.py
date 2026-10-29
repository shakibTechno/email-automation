"""
Views for the Email Campaigns app.
"""
import logging
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import Campaign, CampaignRecipient, ABTest, ABTestVariant
from .serializers import (
    CampaignSerializer,
    CampaignListSerializer,
    CampaignCreateSerializer,
    CampaignUpdateSerializer,
    CampaignSendSerializer,
    CampaignTestEmailSerializer,
    CampaignRecipientSerializer,
    ABTestSerializer,
    ABTestCreateUpdateSerializer,
    DeclareWinnerSerializer,
)
from .filters import CampaignFilter
from .services import CampaignService, ABTestService

logger = logging.getLogger(__name__)


class CampaignViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Campaign model.

    Provides CRUD operations and additional actions:
    - duplicate: Clone a campaign as draft
    - send: Mark campaign for sending or scheduling
    - pause: Pause a scheduled campaign
    - cancel: Cancel a scheduled/paused campaign
    - send_test: Send a test email
    - preview: Preview rendered campaign HTML
    - recipients: List campaign recipients
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CampaignFilter
    search_fields = ['name', 'subject']
    ordering_fields = ['name', 'status', 'scheduled_at', 'sent_at', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return campaigns for the user's organization."""
        return Campaign.objects.filter(
            organization=self.request.user.organization
        ).select_related('template', 'created_by')

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return CampaignListSerializer
        elif self.action == 'create':
            return CampaignCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CampaignUpdateSerializer
        return CampaignSerializer

    def perform_create(self, serializer):
        """Set organization and created_by from the authenticated user."""
        # The creator's personal reply-to is a DEFAULT, applied once here and
        # then owned by the record. It is deliberately not consulted at send
        # time: a scheduled campaign is sent by a worker with no current user.
        extra = {}
        if not serializer.validated_data.get('reply_to_email'):
            extra['reply_to_email'] = self.request.user.reply_to_email
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
            **extra,
        )

    @extend_schema(description="Soft delete a campaign")
    def destroy(self, request, *args, **kwargs):
        """Soft delete a campaign."""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Duplicate a campaign as a new draft",
        responses={201: CampaignSerializer}
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Clone a campaign as a new draft."""
        original = self.get_object()

        # Generate unique name
        base_name = f"{original.name} (Copy)"
        name = base_name
        counter = 1
        while Campaign.objects.filter(
            organization=request.user.organization, name=name
        ).exists():
            counter += 1
            name = f"{original.name} (Copy {counter})"

        clone = Campaign.objects.create(
            organization=request.user.organization,
            name=name,
            status='draft',
            template=original.template,
            subject=original.subject,
            preheader_text=original.preheader_text,
            sender_name=original.sender_name,
            sender_email=original.sender_email,
            reply_to_email=original.reply_to_email,
            recipient_type=original.recipient_type,
            created_by=request.user,
        )
        # Copy M2M tags
        clone.recipient_tags.set(original.recipient_tags.all())

        serializer = CampaignSerializer(clone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        description="Send or schedule a campaign",
        request=CampaignSendSerializer,
        responses={200: CampaignSerializer}
    )
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Validate and mark campaign for sending or scheduling."""
        campaign = self.get_object()

        if campaign.status not in ('draft', 'scheduled'):
            return Response(
                {'error': 'Campaign can only be sent from draft or scheduled status.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate campaign is ready
        errors = []
        if not campaign.template:
            errors.append('Campaign must have a template.')
        if not campaign.subject:
            errors.append('Campaign must have a subject line.')
        if not campaign.sender_name:
            errors.append('Campaign must have a sender name.')
        if not campaign.sender_email:
            errors.append('Campaign must have a sender email.')

        if errors:
            return Response(
                {'errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CampaignSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Calculate recipient count
        recipient_count = CampaignService.get_recipient_count(campaign)
        if recipient_count == 0:
            return Response(
                {'error': 'No recipients found for this campaign.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Quota is checked here, before anything is queued, because this is the
        # only point where the full recipient count is known. Checking it
        # per-batch instead would send to part of the audience and stop — worse
        # than not sending at all, since half the list gets an offer the rest
        # never sees.
        from apps.billing.services import BillingService
        allowed, quota = BillingService.check_email_quota(
            campaign.organization, recipient_count
        )
        if not allowed:
            return Response(
                {
                    'error': (
                        f'This campaign needs {recipient_count:,} emails but only '
                        f'{quota["remaining"]:,} remain on your plan this month '
                        f'({quota["used"]:,} of {quota["limit"]:,} used). '
                        'Upgrade your plan or reduce the audience.'
                    ),
                    'quota': quota,
                    'required': recipient_count,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        campaign.recipient_count = recipient_count

        # Check for A/B test
        try:
            ab_test = campaign.ab_test
            has_ab = ab_test.status == 'draft'
        except ABTest.DoesNotExist:
            ab_test = None
            has_ab = False

        if serializer.validated_data.get('send_now'):
            campaign.status = 'sending'
            campaign.sent_at = timezone.now()
            campaign.save()
            if has_ab:
                ABTestService.prepare_ab_recipients(campaign, ab_test)
                ab_test.status = 'testing'
                ab_test.save(update_fields=['status', 'updated_at'])
                from .tasks import send_ab_variant_emails, check_ab_winner, notify_ab_manual_winner_needed
                send_ab_variant_emails.delay(str(campaign.id), 'a')
                send_ab_variant_emails.delay(str(campaign.id), 'b')
                if ab_test.winner_selection == 'auto':
                    check_ab_winner.apply_async(
                        args=[str(ab_test.id)],
                        countdown=ab_test.test_duration_hours * 3600,
                    )
                else:
                    notify_ab_manual_winner_needed.apply_async(
                        args=[str(ab_test.id)],
                        countdown=ab_test.test_duration_hours * 3600,
                    )
            else:
                CampaignService.prepare_recipients(campaign)
                from .tasks import send_campaign_emails
                send_campaign_emails.delay(str(campaign.id))
        else:
            campaign.status = 'scheduled'
            campaign.scheduled_at = serializer.validated_data.get('scheduled_at')
            campaign.save()

        response_serializer = CampaignSerializer(campaign)
        return Response(response_serializer.data)

    @extend_schema(
        description="Pause a scheduled campaign",
        responses={200: CampaignSerializer}
    )
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a scheduled campaign."""
        campaign = self.get_object()

        if campaign.status != 'scheduled':
            return Response(
                {'error': 'Only scheduled campaigns can be paused.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campaign.status = 'paused'
        campaign.save(update_fields=['status', 'updated_at'])

        serializer = CampaignSerializer(campaign)
        return Response(serializer.data)

    @extend_schema(
        description="Resume a paused campaign and continue sending to the "
                    "recipients that have not yet received it",
        responses={200: CampaignSerializer}
    )
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """
        Resume a paused campaign.

        There was no way back from 'paused' before this: a campaign paused for
        exhausting the plan's monthly allowance would have stayed there even
        after an upgrade or the monthly reset, because nothing could move it
        out of that status.

        Only the recipients still marked 'pending' are sent to, so resuming
        never re-sends to anyone who already received it.
        """
        campaign = self.get_object()

        if campaign.status != 'paused':
            return Response(
                {'error': 'Only paused campaigns can be resumed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        remaining = CampaignRecipient.objects.filter(
            campaign=campaign, status='pending'
        ).count()

        # Nothing left to send: this was paused after everything went out, so
        # settle it rather than putting it back into 'sending' where the
        # completion check would never run again.
        if remaining == 0:
            campaign.status = 'sent'
            campaign.completed_at = timezone.now()
            campaign.save(update_fields=['status', 'completed_at', 'updated_at'])
            return Response(CampaignSerializer(campaign).data)

        from apps.billing.services import BillingService
        allowed, quota = BillingService.check_email_quota(campaign.organization, remaining)
        if not allowed:
            return Response(
                {
                    'error': (
                        f'{remaining:,} recipients are still waiting but only '
                        f'{quota["remaining"]:,} emails remain on your plan this '
                        'month. Upgrade your plan to resume.'
                    ),
                    'quota': quota,
                    'required': remaining,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        campaign.status = 'sending'
        if not campaign.sent_at:
            campaign.sent_at = timezone.now()
        campaign.save(update_fields=['status', 'sent_at', 'updated_at'])

        from .tasks import send_campaign_emails
        send_campaign_emails.delay(str(campaign.id))

        return Response(CampaignSerializer(campaign).data)

    @extend_schema(
        description="Cancel a scheduled or paused campaign",
        responses={200: CampaignSerializer}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a scheduled or paused campaign."""
        campaign = self.get_object()

        if campaign.status not in ('scheduled', 'paused'):
            return Response(
                {'error': 'Only scheduled or paused campaigns can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campaign.status = 'cancelled'
        campaign.save(update_fields=['status', 'updated_at'])

        serializer = CampaignSerializer(campaign)
        return Response(serializer.data)

    @extend_schema(
        description="Archive a sent or cancelled campaign",
        responses={200: CampaignSerializer}
    )
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a sent or cancelled campaign to hide it from the default view."""
        campaign = self.get_object()

        if campaign.status not in ('sent', 'cancelled'):
            return Response(
                {'error': 'Only sent or cancelled campaigns can be archived.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campaign.status = 'archived'
        campaign.save(update_fields=['status', 'updated_at'])

        serializer = CampaignSerializer(campaign)
        return Response(serializer.data)

    @extend_schema(
        description="Send a test email",
        request=CampaignTestEmailSerializer,
        responses={200: {"type": "object"}}
    )
    @action(detail=True, methods=['post'], url_path='send_test')
    def send_test(self, request, pk=None):
        """Send a test email to specified addresses."""
        campaign = self.get_object()

        serializer = CampaignTestEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        test_emails = serializer.validated_data['test_emails']

        try:
            count = CampaignService.send_test_email(campaign, test_emails)
            return Response({
                'message': f'Test email sent to {count} recipient(s).',
                'recipients': test_emails,
            })
        except Exception as e:
            logger.error(f"Test email failed for campaign {campaign.id}: {e}")
            return Response(
                {'error': f'Failed to send test email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        description="Preview rendered campaign HTML",
        responses={200: {"type": "object"}}
    )
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Return rendered HTML preview of the campaign."""
        campaign = self.get_object()

        html = CampaignService.render_html(campaign)

        return Response({
            'html': html,
            'subject': campaign.subject,
        })

    @extend_schema(
        description="List campaign recipients",
        responses={200: CampaignRecipientSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def recipients(self, request, pk=None):
        """List recipients for a campaign with pagination."""
        campaign = self.get_object()
        queryset = CampaignRecipient.objects.filter(
            campaign=campaign
        ).select_related('contact')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CampaignRecipientSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CampaignRecipientSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(description="Get, create, update, or delete the A/B test for this campaign")
    @action(detail=True, methods=['get', 'post', 'put', 'delete'], url_path='ab-test')
    def ab_test_config(self, request, pk=None):
        """Manage the A/B test configuration for a campaign."""
        campaign = self.get_object()

        if request.method == 'GET':
            try:
                ab_test = campaign.ab_test
                return Response(ABTestSerializer(ab_test).data)
            except ABTest.DoesNotExist:
                return Response({'detail': 'No A/B test configured.'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'DELETE':
            try:
                ab_test = campaign.ab_test
                if ab_test.status != 'draft':
                    return Response({'error': 'Cannot delete an active A/B test.'}, status=status.HTTP_400_BAD_REQUEST)
                ab_test.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except ABTest.DoesNotExist:
                return Response(status=status.HTTP_204_NO_CONTENT)

        # POST / PUT — create or update
        if campaign.status not in ('draft', 'scheduled'):
            return Response({'error': 'Cannot configure A/B test after campaign is sent.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ABTestCreateUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        # Resolve variant B template if provided
        variant_b_template = None
        if d.get('variant_b_template'):
            from apps.templates.models import EmailTemplate as ET
            try:
                variant_b_template = ET.objects.get(id=d['variant_b_template'], organization=request.user.organization)
            except ET.DoesNotExist:
                return Response({'error': 'Template not found.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ab_test = campaign.ab_test
            if ab_test.status != 'draft':
                return Response({'error': 'Cannot modify an active A/B test.'}, status=status.HTTP_400_BAD_REQUEST)
        except ABTest.DoesNotExist:
            ab_test = None

        if ab_test is None:
            ab_test = ABTest.objects.create(
                campaign=campaign,
                test_type=d['test_type'],
                test_percentage=d['test_percentage'],
                winner_criteria=d['winner_criteria'],
                winner_selection=d['winner_selection'],
                test_duration_hours=d['test_duration_hours'],
            )
        else:
            ab_test.test_type = d['test_type']
            ab_test.test_percentage = d['test_percentage']
            ab_test.winner_criteria = d['winner_criteria']
            ab_test.winner_selection = d['winner_selection']
            ab_test.test_duration_hours = d['test_duration_hours']
            ab_test.save()
            ab_test.variants.all().delete()

        # Create Variant A (control = campaign's values)
        ABTestVariant.objects.create(
            ab_test=ab_test,
            variant='a',
            subject=campaign.subject,
            sender_name=campaign.sender_name,
            template=campaign.template,
        )
        # Create Variant B (challenger)
        ABTestVariant.objects.create(
            ab_test=ab_test,
            variant='b',
            subject=d.get('variant_b_subject', '') or campaign.subject,
            sender_name=d.get('variant_b_sender_name', '') or campaign.sender_name,
            template=variant_b_template if d['test_type'] == 'content' else campaign.template,
        )

        return Response(ABTestSerializer(ab_test).data, status=status.HTTP_201_CREATED)

    @extend_schema(description="Manually declare the winner of an A/B test")
    @action(detail=True, methods=['post'], url_path='declare-winner')
    def declare_winner(self, request, pk=None):
        """Manually set the winner variant and send to remaining recipients."""
        campaign = self.get_object()
        try:
            ab_test = campaign.ab_test
        except ABTest.DoesNotExist:
            return Response({'error': 'No A/B test found.'}, status=status.HTTP_404_NOT_FOUND)

        if ab_test.status not in ('testing', 'winner_declared'):
            return Response({'error': 'Cannot declare winner at this stage.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DeclareWinnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        winner = serializer.validated_data['winner']

        ab_test.winner_variant = winner
        ab_test.status = 'winner_declared'
        ab_test.save(update_fields=['winner_variant', 'status', 'updated_at'])

        ABTestService.compute_variant_stats(ab_test)

        from .tasks import send_ab_winner_to_remainder
        send_ab_winner_to_remainder.delay(str(ab_test.id))

        return Response(ABTestSerializer(ab_test).data)
