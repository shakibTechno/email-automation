"""
Models for the Email Campaigns app.
"""
from django.db import models
from django.db.models import Q
from django.conf import settings
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Organization
from apps.contacts.models import Contact, Tag
from apps.templates.models import EmailTemplate
import uuid


class CampaignManager(models.Manager):
    """Manager for Campaign model that excludes soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Campaign(TimeStampedModel, SoftDeleteModel):
    """
    Campaign model for email marketing campaigns.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('archived', 'Archived'),
    ]

    RECIPIENT_TYPE_CHOICES = [
        ('all_subscribed', 'All Subscribed Contacts'),
        ('by_tags', 'By Tags'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='campaigns'
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Email content
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns'
    )
    subject = models.CharField(max_length=255, blank=True)
    preheader_text = models.CharField(max_length=255, blank=True)

    # Sender info
    sender_name = models.CharField(max_length=255, blank=True)
    sender_email = models.EmailField(blank=True)
    reply_to_email = models.EmailField(blank=True)

    # Recipients
    recipient_type = models.CharField(
        max_length=20,
        choices=RECIPIENT_TYPE_CHOICES,
        default='all_subscribed'
    )
    recipient_tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='campaigns'
    )
    recipient_count = models.PositiveIntegerField(default=0)

    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns'
    )

    objects = CampaignManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'campaigns'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class CampaignRecipient(TimeStampedModel):
    """
    Tracks individual recipients for a campaign.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('complained', 'Complained'),
        ('unsubscribed', 'Unsubscribed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='campaign_recipients'
    )
    email = models.EmailField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    complained_at = models.DateTimeField(null=True, blank=True)
    # A/B test variant: 'a', 'b', 'winner' (waiting for winner), or null (no AB test)
    ab_variant = models.CharField(max_length=10, null=True, blank=True, db_index=True)

    # ── Provider correlation ──────────────────────────────────────────────────
    # Postal's per-recipient identifiers, captured from the send response. Every
    # webhook carries both, and they are the only reliable way to match a
    # delivery event back to this row — Postal does not echo custom headers.
    postal_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    postal_token = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        db_table = 'campaign_recipients'
        ordering = ['-created_at']
        unique_together = [['campaign', 'contact']]
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['contact']),
            models.Index(fields=['tracking_id']),
        ]

    def __str__(self):
        return f"{self.campaign.name} -> {self.email}"

    # Engagement is a funnel, but the events that report it arrive out of order:
    # a provider's "delivered" webhook routinely lands after the open pixel has
    # already fired. Since `status` is a single column, a naive write rewinds
    # 'opened' back to 'delivered' and the campaign under-reports engagement.
    # These ranks let a write move the status forward only.
    STATUS_RANK = {
        'pending': 0,
        'sent': 1,
        'delivered': 2,
        'opened': 3,
        'clicked': 4,
    }
    # Outcomes that end the line. They always win, whatever the current status,
    # because they change whether this contact may be mailed again.
    TERMINAL_STATUSES = frozenset({'bounced', 'complained', 'unsubscribed', 'failed'})

    # States that cannot be reached unless the message arrived — you cannot
    # open, click or unsubscribe from mail that never landed.
    DELIVERED_STATUSES = ('delivered', 'opened', 'clicked', 'unsubscribed', 'complained')

    @classmethod
    def delivered_filter(cls):
        """
        Everything that counts as delivered.

        Defined here because three call sites each had their own version and
        they disagreed: the dashboard asked for `status='delivered'` alone,
        which silently drops every recipient who went on to open or click,
        since `status` advances through the funnel. A campaign to two people,
        one of whom clicked, read as 2 delivered on the campaign report and 1
        on the dashboard.

        Two independent kinds of evidence are accepted: an explicit delivery
        timestamp from the provider's webhook, or a status that implies
        delivery. The timestamp alone is not enough, because a provider
        without delivery webhooks (plain SMTP) never sets it.
        """
        return Q(delivered_at__isnull=False) | Q(status__in=cls.DELIVERED_STATUSES)

    @classmethod
    def bounced_filter(cls):
        """Bounced, by timestamp or terminal status — same reasoning as above."""
        return Q(bounced_at__isnull=False) | Q(status='bounced')

    def advance_status(self, new_status, extra_fields=None):
        """
        Move `status` forward, never backwards, and save.

        Returns True if the status changed. Timestamp fields passed in
        `extra_fields` are always written, even when the status itself does not
        move, because analytics counts opens and clicks from the timestamps
        rather than from `status`.
        """
        fields = dict(extra_fields or {})
        changed = False

        if self.status not in self.TERMINAL_STATUSES:
            if new_status in self.TERMINAL_STATUSES:
                changed = self.status != new_status
            else:
                current = self.STATUS_RANK.get(self.status, 0)
                incoming = self.STATUS_RANK.get(new_status, 0)
                changed = incoming > current

        if changed:
            self.status = new_status

        for name, value in fields.items():
            setattr(self, name, value)

        update_fields = list(fields.keys())
        if changed:
            update_fields.append('status')
        if update_fields:
            self.save(update_fields=update_fields + ['updated_at'])
        return changed


class CampaignLink(TimeStampedModel):
    """Stores unique links in a campaign for click tracking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='links'
    )
    original_url = models.TextField()
    position = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'campaign_links'
        unique_together = [['campaign', 'original_url']]
        indexes = [
            models.Index(fields=['campaign']),
        ]

    def __str__(self):
        return f"{self.campaign.name} -> {self.original_url[:50]}"


class CampaignLinkClick(TimeStampedModel):
    """Records individual click events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    link = models.ForeignKey(
        CampaignLink,
        on_delete=models.CASCADE,
        related_name='clicks'
    )
    recipient = models.ForeignKey(
        CampaignRecipient,
        on_delete=models.CASCADE,
        related_name='link_clicks'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = 'campaign_link_clicks'
        indexes = [
            models.Index(fields=['link']),
            models.Index(fields=['recipient']),
        ]

    def __str__(self):
        return f"Click on {self.link.original_url[:50]} by {self.recipient.email}"


class ABTest(TimeStampedModel):
    """A/B test configuration linked to a campaign."""

    TEST_TYPE_CHOICES = [
        ('subject', 'Subject Line'),
        ('sender_name', 'Sender Name'),
        ('content', 'Email Content'),
    ]
    WINNER_CRITERIA_CHOICES = [
        ('open_rate', 'Open Rate'),
        ('click_rate', 'Click Rate'),
    ]
    WINNER_SELECTION_CHOICES = [
        ('auto', 'Automatic'),
        ('manual', 'Manual'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('testing', 'Testing'),
        ('winner_declared', 'Winner Declared'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.OneToOneField(
        Campaign, on_delete=models.CASCADE, related_name='ab_test'
    )
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES)
    # % of total recipients used for the test (split equally between A and B)
    test_percentage = models.PositiveIntegerField(default=20)
    winner_criteria = models.CharField(
        max_length=20, choices=WINNER_CRITERIA_CHOICES, default='open_rate'
    )
    winner_selection = models.CharField(
        max_length=20, choices=WINNER_SELECTION_CHOICES, default='auto'
    )
    test_duration_hours = models.PositiveIntegerField(default=4)
    winner_variant = models.CharField(max_length=1, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    winner_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'campaign_ab_tests'

    def __str__(self):
        return f"A/B Test for {self.campaign.name} ({self.test_type})"


class ABTestVariant(TimeStampedModel):
    """One variant (A or B) within an A/B test."""

    VARIANT_CHOICES = [('a', 'Variant A'), ('b', 'Variant B')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ab_test = models.ForeignKey(
        ABTest, on_delete=models.CASCADE, related_name='variants'
    )
    variant = models.CharField(max_length=1, choices=VARIANT_CHOICES)

    # Override values — which field is used depends on ab_test.test_type
    subject = models.CharField(max_length=500, blank=True)
    sender_name = models.CharField(max_length=200, blank=True)
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ab_variants',
    )

    # Cached stats updated after sending
    recipient_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    open_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'campaign_ab_test_variants'
        unique_together = [('ab_test', 'variant')]

    def __str__(self):
        return f"Variant {self.variant.upper()} – {self.ab_test.campaign.name}"

    @property
    def open_rate(self):
        return round(self.open_count / self.sent_count * 100, 1) if self.sent_count else 0.0

    @property
    def click_rate(self):
        return round(self.click_count / self.sent_count * 100, 1) if self.sent_count else 0.0
