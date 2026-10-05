"""
Models for per-organization email configuration.
"""
import uuid
from django.db import models
from apps.core.models import TimeStampedModel
from apps.accounts.models import Organization


class EmailConfiguration(TimeStampedModel):
    """
    One row per organization. Stores sending identity, SMTP/provider credentials,
    compliance settings, and sending limits.
    """
    PROVIDER_CHOICES = [
        ('platform_default', 'Platform Default (shared SMTP)'),
        ('smtp', 'Custom SMTP'),
        ('sendgrid', 'SendGrid'),
        ('mailgun', 'Mailgun'),
        ('ses', 'Amazon SES'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name='email_config'
    )

    # ── Sending Identity ──────────────────────────────────────────────────────
    from_name = models.CharField(max_length=255, blank=True)
    from_email = models.EmailField(blank=True)
    reply_to_email = models.EmailField(blank=True)

    # ── Provider / SMTP ───────────────────────────────────────────────────────
    provider = models.CharField(
        max_length=30, choices=PROVIDER_CHOICES, default='platform_default'
    )
    # SMTP fields
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=512, blank=True)  # stored as-is; mask in serializer
    smtp_use_tls = models.BooleanField(default=True)
    smtp_use_ssl = models.BooleanField(default=False)
    # Generic API key (SendGrid / Mailgun / SES)
    api_key = models.CharField(max_length=512, blank=True)
    # Mailgun domain / SES region
    provider_domain = models.CharField(max_length=255, blank=True)
    provider_region = models.CharField(max_length=50, blank=True, default='us-east-1')

    # ── Compliance (CAN-SPAM / GDPR) ──────────────────────────────────────────
    physical_address = models.TextField(blank=True)
    email_footer_text = models.TextField(blank=True)
    unsubscribe_redirect_url = models.URLField(
        blank=True,
        help_text='Custom URL contacts land on after unsubscribing. Leave blank to use platform default.'
    )

    # ── Sending Limits ────────────────────────────────────────────────────────
    daily_send_limit = models.PositiveIntegerField(
        default=0, help_text='Max emails per day. 0 = unlimited.'
    )
    hourly_send_limit = models.PositiveIntegerField(
        default=0, help_text='Max emails per hour. 0 = unlimited.'
    )

    # ── Deliverability Guards ─────────────────────────────────────────────────
    bounce_threshold_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        help_text='Auto-pause sending if bounce rate exceeds this %.'
    )
    complaint_threshold_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.10,
        help_text='Auto-pause sending if complaint rate exceeds this %.'
    )
    # Set to True by admin when thresholds are breached
    sending_paused_due_to_threshold = models.BooleanField(default=False)

    class Meta:
        db_table = 'org_email_configs'

    def __str__(self):
        return f"EmailConfig for {self.organization.name}"


class SendingDomain(TimeStampedModel):
    """
    A verified sending domain for an organization.
    Platform generates DNS records; user copies them to their DNS provider.
    """
    STATUS_PENDING = 'pending'
    STATUS_VERIFIED = 'verified'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='sending_domains'
    )
    domain = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    verified_at = models.DateTimeField(null=True, blank=True)

    # DNS records to add
    spf_record = models.TextField(blank=True)
    dkim_selector = models.CharField(max_length=64, blank=True)
    dkim_public_key = models.TextField(blank=True)
    dkim_record_name = models.CharField(max_length=255, blank=True)
    dkim_record_value = models.TextField(blank=True)

    # Latest verification attempt detail
    last_check_at = models.DateTimeField(null=True, blank=True)
    last_check_error = models.TextField(blank=True)

    class Meta:
        db_table = 'sending_domains'
        unique_together = [['organization', 'domain']]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.domain} ({self.status})"
