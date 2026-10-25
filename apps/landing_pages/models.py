"""
Models for the Landing Pages app.
"""
import secrets
import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from apps.core.models import TimeStampedModel, SoftDeleteModel


def _new_verification_token():
    return secrets.token_urlsafe(24)


class LandingDomain(TimeStampedModel):
    """
    A hostname an organization has connected for serving its own landing pages.

    The hostname is not decoration: it is how a request identifies the tenant.
    Page slugs are unique per organization rather than globally, so
    `go.customer.com/pricing` resolves unambiguously where `/p/pricing` cannot.
    That is also why `domain` is unique across the whole table — two tenants
    claiming one hostname would make the lookup ambiguous again, this time with
    no way to break the tie.

    Shaped after `email_config.SendingDomain`, deliberately: an operator
    debugging "my domain does not work" should find the same fields in the same
    places whichever kind of domain it is.
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
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='landing_domains',
    )
    domain = models.CharField(max_length=255, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # The organization's default. Pages that do not pin a domain use this one.
    is_primary = models.BooleanField(default=False)

    # Echoed back at /.well-known/mailflow-domain-verification/<token>/ so a
    # fetch against the customer's own hostname proves the traffic reaches us.
    verification_token = models.CharField(max_length=64, default=_new_verification_token)

    verified_at = models.DateTimeField(null=True, blank=True)
    last_check_at = models.DateTimeField(null=True, blank=True)
    last_check_error = models.TextField(blank=True)
    # Set when a request actually arrives for this host — the difference
    # between "DNS is wrong" and "DNS is right but nobody has visited".
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'landing_domains'
        ordering = ['-is_primary', 'domain']
        indexes = [
            models.Index(fields=['organization', 'is_primary']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.domain

    @property
    def is_verified(self):
        return self.status == self.STATUS_VERIFIED

    @property
    def base_url(self):
        return f"https://{self.domain}"

    @property
    def verification_url(self):
        """Where `verify()` looks for the token. Also shown in the UI."""
        return f"{self.base_url}/.well-known/mailflow-domain-verification/{self.verification_token}/"

    @property
    def dns_record(self):
        """The record the customer publishes, rendered by the settings page."""
        return {
            'type': 'CNAME',
            'host': self.domain,
            'value': getattr(settings, 'LANDING_DOMAIN_CNAME_TARGET', '') or '',
        }

    def clean(self):
        from .domains import normalize_domain, reserved_domain_error

        self.domain = normalize_domain(self.domain)
        error = reserved_domain_error(self.domain)
        if error:
            raise ValidationError({'domain': error})

    def save(self, *args, **kwargs):
        from .domains import normalize_domain

        self.domain = normalize_domain(self.domain)
        # First domain an organization connects becomes its default, or pages
        # would have nowhere to resolve to until someone pressed a button.
        if self.is_primary is False and not LandingDomain.objects.filter(
            organization_id=self.organization_id
        ).exclude(pk=self.pk).exists():
            self.is_primary = True
        super().save(*args, **kwargs)


class LandingPageManager(models.Manager):
    """Manager for LandingPage that excludes soft-deleted items by default."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def with_deleted(self):
        """Include soft-deleted items in queryset."""
        return super().get_queryset()


class LandingPage(TimeStampedModel, SoftDeleteModel):
    """
    Landing page model for building and publishing marketing pages.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='landing_pages'
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Content
    html_content = models.TextField(blank=True, default='')
    design_json = models.JSONField(default=dict, blank=True)
    css_content = models.TextField(blank=True, default='')

    # SEO
    seo_title = models.CharField(max_length=70, blank=True, default='')
    seo_description = models.CharField(max_length=160, blank=True, default='')
    seo_keywords = models.CharField(max_length=255, blank=True, default='')
    og_image = models.ImageField(
        upload_to='landing_pages/og_images/',
        blank=True,
        null=True
    )

    # Settings
    favicon = models.ImageField(
        upload_to='landing_pages/favicons/',
        blank=True,
        null=True
    )
    google_analytics_id = models.CharField(max_length=20, blank=True, default='')
    facebook_pixel_id = models.CharField(max_length=20, blank=True, default='')
    custom_head_code = models.TextField(blank=True, default='')
    custom_body_code = models.TextField(blank=True, default='')

    # Form Integration
    form = models.ForeignKey(
        'forms.Form',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='landing_pages'
    )

    # Which of the organization's connected domains serves this page. Null means
    # the organization's primary domain, so connecting a domain moves every page
    # at once rather than requiring each to be edited.
    domain = models.ForeignKey(
        'landing_pages.LandingDomain',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pages',
    )
    # Serve this page at the domain root. At most one per domain; enforced in
    # the service rather than the database because it is a per-domain rule on a
    # nullable relation.
    is_domain_home = models.BooleanField(default=False)

    # Analytics (cached)
    view_count = models.PositiveIntegerField(default=0)
    conversion_count = models.PositiveIntegerField(default=0)

    # Metadata
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_landing_pages'
    )

    objects = LandingPageManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'landing_pages'
        ordering = ['-created_at']
        unique_together = ['organization', 'slug']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'slug']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        """Generate a unique slug for this landing page."""
        base_slug = slugify(self.name)[:90]
        slug = base_slug
        counter = 1
        while LandingPage.all_objects.filter(
            organization=self.organization,
            slug=slug
        ).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    @property
    def serving_domain(self):
        """
        The connected domain this page is served from, or None.

        Only a *verified* domain counts. An unverified one has no certificate
        and no working DNS, so treating it as live would hand the customer a
        link that does not load — worse than a platform link that does.
        """
        if self.domain_id is not None:
            return self.domain if self.domain and self.domain.is_verified else None
        return (
            LandingDomain.objects
            .filter(
                organization_id=self.organization_id,
                is_primary=True,
                status=LandingDomain.STATUS_VERIFIED,
            )
            .first()
        )

    @property
    def platform_url(self):
        """The address on the platform's own host, which always works."""
        # Landing pages are served by Django, so use BACKEND_URL (not FRONTEND_URL)
        backend_url = getattr(settings, 'BACKEND_URL', 'http://localhost:8000').rstrip('/')
        # Organization-scoped: slugs are unique per tenant, so /p/<slug> alone
        # identifies a page only while no other tenant has chosen the same one.
        return f"{backend_url}/p/{self.organization.slug}/{self.slug}"

    @property
    def public_url(self):
        """
        Where to send people for this page.

        Every surface reads this one property — serializers, admin, the OG tags,
        and both frontend copy-link buttons — so a page's address moves to the
        customer's own domain the moment that domain verifies, with nothing else
        to change.
        """
        domain = self.serving_domain
        if domain is None:
            return self.platform_url
        if self.is_domain_home:
            return domain.base_url
        return f"{domain.base_url}/{self.slug}"

    @property
    def conversion_rate(self):
        """Calculate conversion rate as percentage."""
        if self.view_count == 0:
            return 0
        return round((self.conversion_count / self.view_count) * 100, 2)


class LandingPageTemplate(TimeStampedModel):
    """
    Pre-built landing page templates that users can start from.
    """
    CATEGORY_CHOICES = [
        ('lead_generation', 'Lead Generation'),
        ('webinar', 'Webinar Registration'),
        ('ebook', 'E-book Download'),
        ('product_launch', 'Product Launch'),
        ('event', 'Event Registration'),
        ('coming_soon', 'Coming Soon'),
        ('thank_you', 'Thank You'),
        ('blank', 'Blank'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='landing_page_templates'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='blank'
    )
    thumbnail = models.ImageField(
        upload_to='landing_pages/templates/thumbnails/',
        blank=True,
        null=True
    )

    # Content
    html_content = models.TextField(default='')
    design_json = models.JSONField(default=dict)
    css_content = models.TextField(blank=True, default='')

    # Flags
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'landing_page_templates'
        ordering = ['-usage_count', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class LandingPageAsset(TimeStampedModel):
    """
    Assets (images, videos) uploaded for use in landing pages.
    """
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='landing_page_assets'
    )
    landing_page = models.ForeignKey(
        LandingPage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='assets'
    )
    file = models.FileField(upload_to='landing_pages/assets/')
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        default='image'
    )
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100, default='')

    class Meta:
        db_table = 'landing_page_assets'
        ordering = ['-created_at']

    def __str__(self):
        return self.file_name

    @property
    def url(self):
        """Return the full URL of the asset."""
        if self.file:
            return self.file.url
        return ''


class PageView(TimeStampedModel):
    """
    Track page views for landing page analytics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    landing_page = models.ForeignKey(
        LandingPage,
        on_delete=models.CASCADE,
        related_name='page_views'
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default='')
    referrer = models.URLField(blank=True, default='', max_length=2000)
    session_id = models.CharField(max_length=64, blank=True, default='')
    is_unique = models.BooleanField(default=True)

    class Meta:
        db_table = 'page_views'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['landing_page', 'created_at']),
            models.Index(fields=['landing_page', 'session_id']),
        ]

    def __str__(self):
        return f"View on {self.landing_page.name} at {self.created_at}"
