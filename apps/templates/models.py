"""
Models for the Email Templates app.
"""
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Organization
import uuid


class EmailTemplateManager(models.Manager):
    """Manager for EmailTemplate model that excludes soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class EmailTemplate(TimeStampedModel, SoftDeleteModel):
    """
    Email template model for storing drag-and-drop email designs.
    """
    CATEGORY_CHOICES = [
        ('marketing', 'Marketing'),
        ('transactional', 'Transactional'),
        ('newsletter', 'Newsletter'),
        ('welcome', 'Welcome'),
        ('notification', 'Notification'),
        ('custom', 'Custom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='email_templates'
    )

    # Template info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='custom'
    )
    subject = models.CharField(max_length=255, blank=True)

    # Design data
    design_json = models.JSONField(default=dict, blank=True)
    html_content = models.TextField(blank=True)
    thumbnail_url = models.URLField(blank=True)

    # Flags
    is_preset = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = EmailTemplateManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'email_templates'
        ordering = ['-created_at']
        unique_together = [['organization', 'name']]
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['organization', 'is_preset']),
            models.Index(fields=['organization', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class TemplateImage(TimeStampedModel):
    """
    Image uploaded for use in email templates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='template_images'
    )
    image = models.ImageField(upload_to='template_images/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'template_images'
        ordering = ['-created_at']

    def __str__(self):
        return self.original_filename
