"""
Views for the Email Sequences app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.permissions import IsOrganizationMember, IsAdminForDestructiveActions
from .models import EmailSequence, SequenceStep, SequenceEnrollment, SequenceStepExecution
from .serializers import (
    EmailSequenceListSerializer,
    EmailSequenceSerializer,
    EmailSequenceCreateSerializer,
    SequenceStepSerializer,
    SequenceEnrollmentSerializer,
    SequenceStepExecutionSerializer,
)
from .filters import SequenceFilter, SequenceEnrollmentFilter
from .services import SequenceService, SequenceEnrollmentService


class EmailSequenceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationMember, IsAdminForDestructiveActions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SequenceFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        return EmailSequence.objects.filter(
            organization=self.request.user.organization,
            deleted_at__isnull=True,
        ).select_related('created_by').prefetch_related('steps', 'enrollments')

    def get_serializer_class(self):
        if self.action == 'list':
            return EmailSequenceListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return EmailSequenceCreateSerializer
        return EmailSequenceSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        sequence = self.get_object()
        if sequence.steps.count() == 0:
            return Response({'error': 'Sequence must have at least one step.'}, status=400)
        sequence.status = 'active'
        sequence.save(update_fields=['status'])
        return Response(EmailSequenceSerializer(sequence).data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        sequence = self.get_object()
        sequence.status = 'paused'
        sequence.save(update_fields=['status'])
        return Response(EmailSequenceSerializer(sequence).data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        sequence = self.get_object()
        new_seq = SequenceService.duplicate_sequence(sequence, created_by=request.user)
        return Response(EmailSequenceSerializer(new_seq).data, status=201)

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        """Enroll one or more contacts by ID list."""
        sequence = self.get_object()
        contact_ids = request.data.get('contact_ids', [])
        if not contact_ids:
            return Response({'error': 'contact_ids is required.'}, status=400)
        result = SequenceEnrollmentService.enroll_contacts_bulk(
            sequence, contact_ids, enrolled_by=request.user
        )
        return Response(result)

    @action(detail=True, methods=['get'])
    def enrollments(self, request, pk=None):
        sequence = self.get_object()
        qs = sequence.enrollments.select_related('contact').order_by('-created_at')
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = SequenceEnrollmentSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        sequence = self.get_object()
        enrollments = sequence.enrollments.all()
        total = enrollments.count()
        active = enrollments.filter(status='active').count()
        completed = enrollments.filter(status='completed').count()
        cancelled = enrollments.filter(status='cancelled').count()
        unsubscribed = enrollments.filter(status='unsubscribed').count()

        step_stats = []
        for step in sequence.steps.order_by('position'):
            execs = step.executions.all()
            sent = execs.filter(status='sent').count()
            step_stats.append({
                'position': step.position,
                'subject': step.subject,
                'sent': sent,
                'opened': execs.filter(opened_at__isnull=False).count(),
                'clicked': execs.filter(clicked_at__isnull=False).count(),
                'open_rate': round(execs.filter(opened_at__isnull=False).count() / sent * 100, 1) if sent else 0,
                'click_rate': round(execs.filter(clicked_at__isnull=False).count() / sent * 100, 1) if sent else 0,
            })

        return Response({
            'total_enrolled': total,
            'active': active,
            'completed': completed,
            'cancelled': cancelled,
            'unsubscribed': unsubscribed,
            'completion_rate': round(completed / total * 100, 1) if total else 0,
            'steps': step_stats,
        })


class SequenceStepViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = SequenceStepSerializer

    def get_queryset(self):
        return SequenceStep.objects.filter(
            sequence__organization=self.request.user.organization,
            sequence__deleted_at__isnull=True,
        ).select_related('template')

    def perform_create(self, serializer):
        """
        Append the new step to the end of its sequence.

        The sequence itself is validated by the serializer against the
        caller's own sequences. This used to read it from `request.data` and
        look it up with an unguarded `.get()`, so a missing or unknown id
        raised DoesNotExist and the API answered 500.
        """
        from django.db.models import Max

        sequence = serializer.validated_data['sequence']
        # max + 1, not count(). After any step is deleted from the middle,
        # count() returns a position that is already taken — three steps at
        # 0,1,2, delete the middle one, and count() is 2 while position 2
        # still exists, so the next create hits the unique constraint as an
        # IntegrityError 500.
        highest = sequence.steps.aggregate(top=Max('position'))['top']
        serializer.save(position=0 if highest is None else highest + 1)

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Accept {sequence_id, step_ids: [...ordered UUIDs...]}"""
        sequence_id = request.data.get('sequence_id')
        step_ids = request.data.get('step_ids', [])
        try:
            sequence = EmailSequence.objects.get(
                id=sequence_id, organization=request.user.organization
            )
        except EmailSequence.DoesNotExist:
            return Response({'error': 'Sequence not found.'}, status=404)
        SequenceService.reorder_steps(sequence, step_ids)
        return Response({'status': 'reordered'})


class SequenceEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = SequenceEnrollmentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = SequenceEnrollmentFilter
    ordering = ['-created_at']

    def get_queryset(self):
        return SequenceEnrollment.objects.filter(
            sequence__organization=self.request.user.organization,
        ).select_related('contact', 'sequence')

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        enrollment = self.get_object()
        SequenceEnrollmentService.cancel_enrollment(enrollment)
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['get'])
    def steps(self, request, pk=None):
        enrollment = self.get_object()
        execs = enrollment.step_executions.select_related('step').order_by('step__position')
        return Response(SequenceStepExecutionSerializer(execs, many=True).data)
