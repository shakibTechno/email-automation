"""
Integration models for the Email Marketing Automation Platform.
"""
import uuid
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel


class AnalyticsIntegration(TimeStampedModel):
    """
    Analytics tracking integrations (Google Analytics, Facebook Pixel, GTM).
    One per provider per organization.
    """
    PROVIDER_CHOICES = [
        ('google_analytics', 'Google Analytics'),
        ('facebook_pixel', 'Facebook Pixel'),
        ('google_tag_manager', 'Google Tag Manager'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='analytics_integrations'
    )
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    tracking_id = models.CharField(max_length=100)
    is_enabled = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'integrations_analytics'
        ordering = ['-created_at']
        unique_together = ['organization', 'provider']

    def __str__(self):
        return f"{self.get_provider_display()} - {self.organization.name}"


class SocialIntegration(TimeStampedModel):
    """
    Social platform integrations for lead capture (Facebook Lead Ads, LinkedIn Lead Gen).
    One per platform per organization.
    """
    PLATFORM_CHOICES = [
        ('facebook_lead_ads', 'Facebook Lead Ads'),
        ('linkedin_lead_gen', 'LinkedIn Lead Gen'),
    ]

    STATUS_CHOICES = [
        ('disconnected', 'Disconnected'),
        ('connected', 'Connected'),
        ('expired', 'Expired'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='social_integrations'
    )
    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='disconnected'
    )

    # OAuth tokens
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # External account info
    external_account_id = models.CharField(max_length=255, blank=True)
    external_account_name = models.CharField(max_length=255, blank=True)

    # Sync settings
    auto_sync = models.BooleanField(default=False)
    sync_interval_minutes = models.IntegerField(default=60)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    # Field mapping: maps platform fields -> Contact fields
    field_mapping = models.JSONField(default=dict, blank=True)

    # Default tag to apply to imported leads
    default_tag = models.ForeignKey(
        'contacts.Tag',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='social_integrations'
    )

    # Stats
    total_leads_imported = models.IntegerField(default=0)

    # Who connected this integration
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='connected_integrations'
    )

    # API credentials (app_id, app_secret, page_id, organization_id)
    credentials = models.JSONField(default=dict, blank=True)

    # Demo mode flag
    is_demo = models.BooleanField(default=False)

    class Meta:
        db_table = 'integrations_social'
        ordering = ['-created_at']
        unique_together = ['organization', 'platform']

    def __str__(self):
        return f"{self.get_platform_display()} - {self.organization.name} ({self.status})"


class LeadSyncLog(TimeStampedModel):
    """
    Log of lead sync operations for social integrations.
    """
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        SocialIntegration,
        on_delete=models.CASCADE,
        related_name='sync_logs'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='running'
    )

    # Sync stats
    leads_found = models.IntegerField(default=0)
    leads_created = models.IntegerField(default=0)
    leads_updated = models.IntegerField(default=0)
    leads_failed = models.IntegerField(default=0)

    # Error tracking
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'integrations_sync_logs'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Sync {self.status} - {self.integration.get_platform_display()} "
            f"({self.leads_created} created, {self.leads_updated} updated)"
        )
