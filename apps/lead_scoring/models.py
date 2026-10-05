"""
Lead Scoring models — scoring rules, score history, and score thresholds.
"""
import uuid
from django.db import models
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Organization
from apps.contacts.models import Contact


class ScoringRule(TimeStampedModel, SoftDeleteModel):
    """
    Org-scoped rule that awards or deducts points from a contact's lead score.

    Demographic rules are re-evaluated on contact field changes.
    Behavioral rules fire immediately when the named event occurs.
    """
    RULE_TYPE_DEMOGRAPHIC = 'demographic'
    RULE_TYPE_BEHAVIORAL = 'behavioral'
    RULE_TYPE_CHOICES = [
        (RULE_TYPE_DEMOGRAPHIC, 'Demographic'),
        (RULE_TYPE_BEHAVIORAL, 'Behavioral'),
    ]

    EVENT_EMAIL_OPENED = 'email_opened'
    EVENT_EMAIL_CLICKED = 'email_clicked'
    EVENT_FORM_SUBMITTED = 'form_submitted'
    EVENT_TAG_ADDED = 'tag_added'
    EVENT_TAG_REMOVED = 'tag_removed'
    EVENT_WORKFLOW_COMPLETED = 'workflow_completed'
    EVENT_UNSUBSCRIBED = 'unsubscribed'
    EVENT_BOUNCED = 'bounced'
    EVENT_CHOICES = [
        (EVENT_EMAIL_OPENED, 'Email Opened'),
        (EVENT_EMAIL_CLICKED, 'Email Clicked'),
        (EVENT_FORM_SUBMITTED, 'Form Submitted'),
        (EVENT_TAG_ADDED, 'Tag Added'),
        (EVENT_TAG_REMOVED, 'Tag Removed'),
        (EVENT_WORKFLOW_COMPLETED, 'Workflow Completed'),
        (EVENT_UNSUBSCRIBED, 'Unsubscribed'),
        (EVENT_BOUNCED, 'Bounced'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='scoring_rules'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES)
    # Positive = award points; negative = deduct points
    points = models.IntegerField()
    is_active = models.BooleanField(default=True)
    # Lower priority value = evaluated first
    priority = models.PositiveIntegerField(default=0)

    # Demographic: {"field": "company", "operator": "is_not_empty", "value": ""}
    condition = models.JSONField(default=dict, blank=True)

    # Behavioral: which event fires this rule
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES, blank=True)

    # Optional scope filter for behavioral rules
    # e.g. {"tag_id": "uuid"} or {"form_id": "uuid"}
    event_filter = models.JSONField(default=dict, blank=True)

    objects = models.Manager()

    class Meta:
        db_table = 'lead_scoring_rules'
        ordering = ['priority', 'name']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['organization', 'rule_type']),
            models.Index(fields=['organization', 'event_type']),
        ]

    def __str__(self):
        sign = '+' if self.points >= 0 else ''
        return f"{self.name} ({sign}{self.points} pts)"


class ScoreHistory(TimeStampedModel):
    """
    Immutable audit log entry for every lead score change.
    Not soft-deletable — history must be preserved for compliance/audit.
    """
    REASON_RULE = 'rule'
    REASON_MANUAL = 'manual'
    REASON_RECALC = 'recalculation'
    REASON_CHOICES = [
        (REASON_RULE, 'Rule Triggered'),
        (REASON_MANUAL, 'Manual Adjustment'),
        (REASON_RECALC, 'Recalculation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='score_history'
    )
    rule = models.ForeignKey(
        ScoringRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history_entries',
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    points_delta = models.IntegerField()
    score_before = models.IntegerField()
    score_after = models.IntegerField()
    # Used for manual adjustments and recalculation notes
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'lead_score_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contact', '-created_at']),
            models.Index(fields=['contact', 'reason']),
        ]

    def __str__(self):
        return (
            f"{self.contact.email}: {self.score_before} → {self.score_after} "
            f"({self.reason})"
        )


class ScoreThreshold(TimeStampedModel):
    """
    Defines a labeled score range for an organization.
    The service uses these to keep Contact.engagement_level in sync with lead_score.

    Example setup:
        Inactive  min_score=0   → engagement_level='none'
        Cold      min_score=10  → engagement_level='low'
        Warm      min_score=40  → engagement_level='medium'
        Hot       min_score=70  → engagement_level='high'
    """
    ENGAGEMENT_LEVEL_CHOICES = Contact.ENGAGEMENT_LEVEL_CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='score_thresholds'
    )
    label = models.CharField(max_length=50)
    # Inclusive lower bound; upper bound is implied by the next threshold's min_score
    min_score = models.IntegerField()
    color = models.CharField(max_length=20, default='blue')
    engagement_level = models.CharField(
        max_length=10,
        choices=ENGAGEMENT_LEVEL_CHOICES,
        default='none',
    )

    class Meta:
        db_table = 'lead_score_thresholds'
        ordering = ['min_score']
        unique_together = [['organization', 'label']]
        indexes = [
            models.Index(fields=['organization', 'min_score']),
        ]

    def __str__(self):
        return f"{self.label} (≥{self.min_score})"
