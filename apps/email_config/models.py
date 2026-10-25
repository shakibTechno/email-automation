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
        ('postal', 'Postal (platform mail server)'),
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


class PostalTenant(TimeStampedModel):
    """
    One Postal mail server per organization.

    Created lazily by PostalProvisioningService the first time an organization
    adds a sending domain, so free signups and abandoned trials never provision
    real mail infrastructure. See mailstack/MULTI-TENANT.md.

    Each tenant is isolated in Postal: its own API key, its own domains, its own
    suppression list and its own send limit. Tenants do share the server's IP
    reputation, which is what the guardrails in guardrails.py protect.
    """
    STATUS_ACTIVE = 'active'
    STATUS_SUSPENDED = 'suspended'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_SUSPENDED, 'Suspended'),
        (STATUS_ERROR, 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name='postal_tenant'
    )

    # Our key for this tenant in the provisioning API. Immutable once set: the
    # provisioner matches on it, so changing it would orphan the mail server.
    # Must satisfy /\A[a-z0-9][a-z0-9-]{0,47}\z/ — see build_external_id().
    external_id = models.CharField(max_length=48, unique=True)
    # Postal's own UUID for the mail server; every provisioner call keys on it.
    postal_tenant_id = models.CharField(max_length=64, blank=True)
    # Returned only on create and on rotation, never readable back from Postal.
    # Stored as-is, like smtp_password above; masked in the serializer.
    api_key = models.CharField(max_length=512, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    suspension_reason = models.TextField(blank=True)

    send_limit_per_hour = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Postal holds mail above this and it must be released by hand, '
                  'so treat it as a circuit breaker rather than a throttle.'
    )
    ip_pool = models.CharField(max_length=100, blank=True)

    # Cached from GET /tenants/:id so the UI can render without a round trip.
    sent_last_hour = models.PositiveIntegerField(default=0)
    queued = models.PositiveIntegerField(default=0)
    held = models.PositiveIntegerField(default=0)
    bounce_rate_30d = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        db_table = 'postal_tenants'

    def __str__(self):
        return f"PostalTenant {self.external_id} ({self.status})"

    @property
    def is_suspended(self):
        return self.status == self.STATUS_SUSPENDED

    @property
    def can_send(self):
        """
        True when this tenant is usable for sending.

        A tenant with no sending-enabled domain cannot send: Postal rejects any
        From address whose domain it has not verified, with
        UnauthenticatedFromAddress.
        """
        if self.status != self.STATUS_ACTIVE or not self.api_key:
            return False
        return self.organization.sending_domains.filter(sending_enabled=True).exists()


class SendingDomain(TimeStampedModel):
    """
    A sending domain for an organization, mirrored from the provisioning API.

    The provisioner is the source of truth: it generates the real DKIM key,
    queries the domain's own nameservers, and enables sending only when SPF,
    DKIM, return-path and DMARC all pass. This model caches that state so the
    settings page renders without a round trip per view.
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

    # The records the customer must publish, as returned by the provisioner:
    # [{purpose, type, host, value, status, error, note}, ...] for spf, dkim,
    # return_path and dmarc. Rendered directly by the settings page.
    dns_records = models.JSONField(default=list, blank=True)
    # Postal's own verdict. Sending is allowed only when this is True.
    sending_enabled = models.BooleanField(default=False)

    # ── Legacy columns ────────────────────────────────────────────────────────
    # Written by the removed generate_dns_records(), which produced a hardcoded
    # placeholder DKIM value. Kept so existing rows are readable; no longer
    # written. dns_records above replaces all of them.
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
