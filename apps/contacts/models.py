"""
Contact models for the Email Marketing Automation Platform.
"""
from django.db import models
from django.conf import settings
from django.core.validators import EmailValidator
from django.utils import timezone
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Organization
import uuid


class ContactManager(models.Manager):
    """Manager for Contact model."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Contact(TimeStampedModel, SoftDeleteModel):
    """
    Contact model for storing email marketing contacts.
    """
    ENGAGEMENT_LEVEL_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('none', 'None'),
    ]

    SOURCE_CHOICES = [
        ('manual', 'Manual Entry'),
        ('import', 'CSV Import'),
        ('api', 'API'),
        ('form', 'Web Form'),
        ('integration', 'Integration'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='contacts'
    )

    # Basic Information
    email = models.EmailField(validators=[EmailValidator()])
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=255, blank=True)
    company_ref = models.ForeignKey(
        'crm.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contacts'
    )
    job_title = models.CharField(max_length=255, blank=True)

    # Engagement Metrics
    lead_score = models.IntegerField(default=0)
    engagement_level = models.CharField(
        max_length=10,
        choices=ENGAGEMENT_LEVEL_CHOICES,
        default='none'
    )

    # Status Fields
    is_subscribed = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)

    # Custom Fields (JSON)
    custom_fields = models.JSONField(default=dict, blank=True)

    # Ownership
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_contacts',
    )

    # Tracking
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='manual'
    )
    last_activity_at = models.DateTimeField(null=True, blank=True)

    objects = ContactManager()
    all_objects = models.Manager()  # Include soft-deleted

    class Meta:
        db_table = 'contacts'
        ordering = ['-created_at']
        unique_together = [['organization', 'email']]
        indexes = [
            models.Index(fields=['organization', 'email']),
            models.Index(fields=['organization', 'is_subscribed']),
            models.Index(fields=['organization', 'engagement_level']),
            models.Index(fields=['email']),
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['company']),
            models.Index(fields=['last_activity_at']),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def full_name(self):
        """Return the contact's full name."""
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.email

    def unsubscribe(self):
        """Unsubscribe the contact."""
        self.is_subscribed = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=['is_subscribed', 'unsubscribed_at'])

    def resubscribe(self):
        """Resubscribe the contact."""
        self.is_subscribed = True
        self.unsubscribed_at = None
        self.save(update_fields=['is_subscribed', 'unsubscribed_at'])

    def mark_bounced(self):
        """Mark the contact as bounced."""
        self.bounced_at = timezone.now()
        self.save(update_fields=['bounced_at'])

    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])


class Tag(TimeStampedModel):
    """
    Tag model for categorizing contacts.
    """
    COLOR_CHOICES = [
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('pink', 'Pink'),
        ('gray', 'Gray'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='tags'
    )
    name = models.CharField(max_length=50)
    color = models.CharField(
        max_length=10,
        choices=COLOR_CHOICES,
        default='blue'
    )
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'tags'
        ordering = ['name']
        unique_together = [['organization', 'name']]
        indexes = [
            models.Index(fields=['organization', 'name']),
        ]

    def __str__(self):
        return self.name


class ContactTag(TimeStampedModel):
    """
    Many-to-many relationship between Contacts and Tags.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='contact_tags'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='contact_tags'
    )

    class Meta:
        db_table = 'contact_tags'
        unique_together = [['contact', 'tag']]
        indexes = [
            models.Index(fields=['contact', 'tag']),
            models.Index(fields=['tag']),
        ]

    def __str__(self):
        return f"{self.contact.email} - {self.tag.name}"


class CustomField(TimeStampedModel):
    """
    Custom field definition for contacts.
    """
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
        ('dropdown', 'Dropdown'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='custom_fields'
    )
    name = models.CharField(max_length=100)
    field_type = models.CharField(
        max_length=10,
        choices=FIELD_TYPE_CHOICES,
        default='text'
    )
    is_required = models.BooleanField(default=False)
    default_value = models.CharField(max_length=255, blank=True)
    dropdown_options = models.JSONField(default=list, blank=True)  # For dropdown type
    help_text = models.TextField(blank=True)

    class Meta:
        db_table = 'custom_fields'
        ordering = ['name']
        unique_together = [['organization', 'name']]
        indexes = [
            models.Index(fields=['organization', 'name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_field_type_display()})"
