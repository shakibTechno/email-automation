"""
Models for the Email Sequences app.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Organization
from apps.contacts.models import Contact
from apps.templates.models import EmailTemplate


class EmailSequence(TimeStampedModel, SoftDeleteModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='sequences')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    sender_name = models.CharField(max_length=255, blank=True)
    sender_email = models.EmailField(blank=True)
    reply_to_email = models.EmailField(blank=True)
    # Contacts are not re-enrolled if they've already completed or are active
    allow_reenrollment = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_sequences'
    )

    objects = models.Manager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'sequences'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
        ]

    def __str__(self):
        return self.name

    @property
    def step_count(self):
        return self.steps.count()

    @property
    def enrolled_count(self):
        return self.enrollments.filter(status='active').count()

    @property
    def completed_count(self):
        return self.enrollments.filter(status='completed').count()


class SequenceStep(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE, related_name='steps')
    position = models.PositiveIntegerField(default=0)
    subject = models.CharField(max_length=500)
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='sequence_steps'
    )
    # Delay from the previous step (or from enrollment for step 1)
    delay_days = models.PositiveIntegerField(default=0)
    delay_hours = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'sequence_steps'
        ordering = ['position']
        unique_together = [['sequence', 'position']]
        indexes = [
            models.Index(fields=['sequence', 'position']),
        ]

    def __str__(self):
        return f"Step {self.position + 1}: {self.subject}"

    @property
    def total_delay_hours(self):
        return self.delay_days * 24 + self.delay_hours


class SequenceEnrollment(TimeStampedModel):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('unsubscribed', 'Unsubscribed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE, related_name='enrollments')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='sequence_enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_step_position = models.PositiveIntegerField(default=0)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    next_send_at = models.DateTimeField(null=True, blank=True, db_index=True)
    enrolled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sequence_enrollments_made'
    )

    class Meta:
        db_table = 'sequence_enrollments'
        ordering = ['-created_at']
        unique_together = [['sequence', 'contact']]
        indexes = [
            models.Index(fields=['sequence', 'status']),
            models.Index(fields=['contact']),
            models.Index(fields=['next_send_at', 'status']),
        ]

    def __str__(self):
        return f"{self.contact.email} in {self.sequence.name}"


class SequenceStepExecution(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(SequenceEnrollment, on_delete=models.CASCADE, related_name='step_executions')
    step = models.ForeignKey(SequenceStep, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    # Tracking
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sequence_step_executions'
        ordering = ['scheduled_at']
        unique_together = [['enrollment', 'step']]
        indexes = [
            models.Index(fields=['enrollment']),
            models.Index(fields=['scheduled_at', 'status']),
        ]

    def __str__(self):
        return f"{self.enrollment.contact.email} - Step {self.step.position + 1}"
