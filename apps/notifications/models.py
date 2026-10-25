"""
Models for the In-App Notifications app.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.accounts.models import Organization


class Notification(TimeStampedModel):
    NOTIFICATION_TYPES = [
        ('campaign_sent', 'Campaign Sent'),
        ('campaign_failed', 'Campaign Failed'),
        ('ab_test_winner_needed', 'A/B Test Winner Needed'),
        ('ab_test_completed', 'A/B Test Completed'),
        ('form_submission', 'Form Submission'),
        ('workflow_failed', 'Workflow Failed'),
        ('billing_trial_expiring', 'Trial Expiring'),
        ('billing_payment_failed', 'Payment Failed'),
        ('billing_subscription_renewed', 'Subscription Renewed'),
        ('team_member_joined', 'Team Member Joined'),
        ('lead_score_threshold', 'Lead Score Threshold Reached'),
        ('sending_paused', 'Sending Paused'),
        ('sending_domain_verified', 'Sending Domain Verified'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} → {self.user_id}: {self.title}"
