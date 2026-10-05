"""
Models for the Contact Segmentation app.
"""
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.accounts.models import Organization
from apps.contacts.models import Contact
import uuid


class Segment(TimeStampedModel):
    """
    Contact segment for targeting in campaigns and automations.
    Supports both static (manual) and dynamic (rule-based) segments.
    """
    SEGMENT_TYPE_CHOICES = [
        ('static', 'Static'),
        ('dynamic', 'Dynamic'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='segments'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Segment type
    segment_type = models.CharField(
        max_length=20,
        choices=SEGMENT_TYPE_CHOICES,
        default='dynamic'
    )

    # Rules for dynamic segments (stored as JSON)
    # Structure:
    # {
    #   "match_type": "all" | "any",
    #   "conditions": [
    #     {"id": "uuid", "field": "email", "operator": "contains", "value": "@gmail.com"},
    #     {"id": "uuid", "field": "tag", "operator": "has_tag", "value": "tag-uuid"},
    #   ],
    #   "groups": [
    #     {"id": "uuid", "match_type": "any", "conditions": [...]}
    #   ]
    # }
    rules = models.JSONField(default=dict, blank=True)

    # Cached statistics
    contact_count = models.PositiveIntegerField(default=0)
    last_calculated_at = models.DateTimeField(null=True, blank=True)

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_segments'
    )

    class Meta:
        db_table = 'segments'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization', 'segment_type']),
            models.Index(fields=['organization', 'name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_segment_type_display()})"

    @property
    def is_static(self):
        return self.segment_type == 'static'

    @property
    def is_dynamic(self):
        return self.segment_type == 'dynamic'


class SegmentMembership(TimeStampedModel):
    """
    Membership record for static segments.
    Tracks which contacts are manually added to a segment.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    segment = models.ForeignKey(
        Segment,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='segment_memberships'
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_segment_memberships'
    )

    class Meta:
        db_table = 'segment_memberships'
        unique_together = [['segment', 'contact']]
        indexes = [
            models.Index(fields=['segment']),
            models.Index(fields=['contact']),
        ]

    def __str__(self):
        return f"{self.contact.email} in {self.segment.name}"
