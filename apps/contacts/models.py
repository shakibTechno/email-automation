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

    # Derived from is_subscribed/bounced_at/complained_at, never set directly
    # — see save(). A column rather than a property so it can be indexed and
    # used in a segment rule, which is what the segment builder already
    # assumed existed.
    STATUS_ACTIVE = 'active'
    STATUS_UNSUBSCRIBED = 'unsubscribed'
    STATUS_BOUNCED = 'bounced'
    STATUS_COMPLAINED = 'complained'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_UNSUBSCRIBED, 'Unsubscribed'),
        (STATUS_BOUNCED, 'Bounced'),
        (STATUS_COMPLAINED, 'Complained'),
    ]

    BOUNCE_TYPE_CHOICES = [
        ('soft', 'Soft'),
        ('hard', 'Hard'),
    ]

    LIFECYCLE_STAGE_CHOICES = [
        ('subscriber', 'Subscriber'),
        ('lead', 'Lead'),
        ('qualified', 'Qualified Lead'),
        ('customer', 'Customer'),
        ('evangelist', 'Evangelist'),
    ]

    SOURCE_CHOICES = [        ('manual', 'Manual Entry'),
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

    # ── Lifecycle ────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE,
    )
    bounce_type = models.CharField(
        max_length=10, choices=BOUNCE_TYPE_CHOICES, blank=True,
        help_text='Soft bounces may recover; a hard bounce should not be retried.',
    )
    complained_at = models.DateTimeField(null=True, blank=True)
    lifecycle_stage = models.CharField(
        max_length=20, choices=LIFECYCLE_STAGE_CHOICES, default='subscriber',
    )

    # ── Address and locale ──────────────────────────────────────────────────
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    region = models.CharField(
        max_length=120, blank=True, help_text='State, province or region.',
    )
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(
        max_length=2, blank=True, help_text='ISO-3166 alpha-2, e.g. GB.',
    )
    # Send-time localisation is impossible without these, and the platform
    # sends both campaigns and sequences.
    timezone = models.CharField(
        max_length=64, blank=True, help_text='IANA name, e.g. Europe/London.',
    )
    locale = models.CharField(
        max_length=10, blank=True, help_text='BCP-47 tag, e.g. en-GB.',
    )

    # ── Consent ─────────────────────────────────────────────────────────────
    # is_verified records that consent exists; these record how and when, which
    # is what has to be produced when consent is challenged.
    consent_at = models.DateTimeField(null=True, blank=True)
    consent_source = models.CharField(
        max_length=255, blank=True,
        help_text='Where consent was given — a form URL, an import file, a contract.',
    )
    opt_in_ip = models.GenericIPAddressField(null=True, blank=True)
    double_opt_in_at = models.DateTimeField(null=True, blank=True)
    # The upstream system's identifier, so repeated syncs update rather than
    # duplicate. Unique per organization, not globally.
    external_id = models.CharField(max_length=255, blank=True, default='')

    # ── Personal ────────────────────────────────────────────────────────────
    salutation = models.CharField(max_length=20, blank=True)
    middle_name = models.CharField(max_length=150, blank=True)
    preferred_name = models.CharField(
        max_length=150, blank=True, help_text='What to call them in an email.',
    )
    date_of_birth = models.DateField(null=True, blank=True)
    mobile_phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(max_length=255, blank=True)
    linkedin_url = models.URLField(max_length=255, blank=True)

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
        constraints = [
            # Per organization, and only for rows that have one: a blank
            # external_id is the normal case and must not collide.
            models.UniqueConstraint(
                fields=['organization', 'external_id'],
                condition=models.Q(external_id__gt=''),
                name='unique_org_external_id',
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'email']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'lifecycle_stage']),
            models.Index(fields=['organization', 'country']),
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

    @property
    def derived_status(self):
        """
        The contact's state, from the flags that actually record it.

        Ordered worst-first: a contact who complained is not merely
        unsubscribed, and a hard bounce is not merely inactive. `status` exists
        as a column so it can be indexed and segmented, but it is computed here
        and written only by save(), because a status maintained alongside the
        flags is a second definition of the same fact — exactly the split that
        made "delivered" mean two different numbers.
        """
        if self.complained_at:
            return self.STATUS_COMPLAINED
        if self.bounced_at:
            return self.STATUS_BOUNCED
        if not self.is_subscribed:
            return self.STATUS_UNSUBSCRIBED
        return self.STATUS_ACTIVE

    def save(self, *args, **kwargs):
        self.status = self.derived_status
        # Callers that save a narrow set of fields (unsubscribe(),
        # mark_bounced()) would otherwise leave the derived column behind.
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            fields = set(update_fields)
            if fields & {'is_subscribed', 'bounced_at', 'complained_at'}:
                fields.add('status')
                kwargs['update_fields'] = tuple(fields)
        super().save(*args, **kwargs)

    def mark_complained(self):
        """A spam complaint. Harsher than an unsubscribe and never automatic."""
        self.complained_at = timezone.now()
        self.is_subscribed = False
        self.save(update_fields=['complained_at', 'is_subscribed'])

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

    def mark_bounced(self, bounce_type='hard'):
        """
        Mark the contact as bounced.

        The type matters: a soft bounce is a full mailbox and may recover, a
        hard bounce is an address that does not exist and must not be retried.
        Treating them alike is how a sender's reputation erodes.
        """
        self.bounced_at = timezone.now()
        self.bounce_type = bounce_type
        self.save(update_fields=['bounced_at', 'bounce_type'])

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
