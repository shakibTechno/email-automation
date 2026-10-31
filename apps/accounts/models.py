"""
User and Organization models for the Email Marketing Automation Platform.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from apps.core.models import TimeStampedModel, SoftDeleteModel
import secrets
import uuid


class OrganizationManager(models.Manager):
    """Manager for Organization model."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Organization(TimeStampedModel, SoftDeleteModel):
    """
    Multi-tenant organization model.
    Each organization represents a company/team using the platform.
    """
    # Kept in step with billing.Plan.PLAN_TYPE_CHOICES. 'business' was missing
    # here while BillingService wrote it into this field on every upgrade —
    # Django only validates choices in full_clean(), which save() skips, so it
    # persisted silently and every plan tuple that listed tiers by hand then
    # excluded paying Business customers.
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('business', 'Business'),
        ('enterprise', 'Enterprise'),
    ]

    # Tiers in ascending order. Gating asks "is this plan at least X", and
    # answering that with a hand-written tuple at each call site is how
    # 'business' came to be missing from three of them. Rank once; compare
    # through plan_at_least().
    PLAN_RANK = {
        'free': 0,
        'starter': 1,
        'professional': 2,
        'business': 3,
        'enterprise': 4,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    domain = models.CharField(max_length=255, blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')

    # Identifies this organization to the website snippet. Public by design --
    # it ships in the page source of the customer's own site -- so it names,
    # it does not authorise. Nothing it unlocks is private: the popups it
    # returns are already fetchable from the public form endpoints.
    tracking_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    tracking_enabled = models.BooleanField(default=True)
    # Off by default. Anonymous page views are personal data under GDPR, and
    # a customer with a consent banner needs the snippet to wait for it --
    # but a customer who has not thought about it yet should not silently
    # collect nothing either, so this is theirs to turn on.
    tracking_requires_consent = models.BooleanField(default=False)

    # Account-level suspension. False blocks login and the whole tenant API
    # while leaving the data intact, so a suspension applied in error costs
    # nothing to undo. Sending is suspended separately and independently — see
    # EmailConfiguration.sending_paused_due_to_threshold — because stopping a
    # tenant's mail is a far more common action than locking them out.
    is_active = models.BooleanField(default=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspension_reason = models.TextField(blank=True)

    # Contact information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Limits based on plan
    max_contacts = models.IntegerField(default=1000)
    max_emails_per_month = models.IntegerField(default=10000)

    objects = OrganizationManager()
    all_objects = models.Manager()  # Include soft-deleted

    class Meta:
        db_table = 'organizations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def plan_at_least(self, minimum):
        """
        True when this organization's plan is `minimum` or higher.

        Use this for feature gating instead of listing tiers inline. An unknown
        plan ranks below everything and is denied, so a value that should not be
        in the column fails closed rather than unlocking features.
        """
        return self.PLAN_RANK.get(self.plan, -1) >= self.PLAN_RANK[minimum]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure slug is unique
            original_slug = self.slug
            counter = 1
            while Organization.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class UserManager(BaseUserManager):
    """Manager for custom User model."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'owner')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel, SoftDeleteModel):
    """
    Custom user model with email as the unique identifier.
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    # Profile information
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.URLField(blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')

    # Where replies should go for campaigns and sequences this user creates.
    # A default stamped onto the campaign at creation, never consulted at send
    # time: a scheduled send runs in a worker with no current user, and an
    # organization's newsletter must not redirect replies to whoever pressed
    # Send. Blank means the organization's reply-to address applies.
    reply_to_email = models.EmailField(blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['organization', 'is_active']),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_organization_owner(self):
        """Check if user is the organization owner."""
        return self.role == 'owner'

    @property
    def is_organization_admin(self):
        """Check if user is an organization admin or owner."""
        return self.role in ['owner', 'admin']

    def has_perm(self, perm, obj=None):
        """Check if user has a specific permission."""
        return self.is_superuser or self.is_staff

    def has_module_perms(self, app_label):
        """Check if user has permissions to view the app."""
        return self.is_superuser or self.is_staff


class PasswordResetToken(TimeStampedModel):
    """
    Token for password reset functionality.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Password reset token for {self.user.email}"

    @property
    def is_expired(self):
        """Check if the token has expired."""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if the token is valid."""
        return not self.is_used and not self.is_expired


class EmailVerificationToken(TimeStampedModel):
    """
    Token for email verification functionality.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verification_tokens')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'email_verification_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Email verification token for {self.user.email}"

    @property
    def is_expired(self):
        """Check if the token has expired."""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if the token is valid."""
        return not self.is_used and not self.is_expired


class TeamInvitation(TimeStampedModel):
    """
    Invitation to join an organization.
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invitations'
    )
    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_invitations'
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Whether the invitation email actually went out. Persisted rather than
    # returned once, because an admin who invited someone yesterday still needs
    # to know it never arrived — and because an invitation that silently fails
    # to send looks identical to one the recipient ignored.
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True)

    class Meta:
        db_table = 'team_invitations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitation for {self.email} to {self.organization.name}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.status == 'pending' and not self.is_expired


class EmailConfiguration(TimeStampedModel):
    """
    Per-organization email configuration.
    Stores sender defaults (all members) and SMTP engine settings (admin/owner only).
    Created automatically on first access via get_or_create.
    """
    BACKEND_CHOICES = [
        ('smtp', 'Custom SMTP'),
        ('console', 'Console (development only)'),
    ]

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='email_configuration',
    )

    # Sender defaults — any member can view/edit
    default_sender_name = models.CharField(max_length=255, blank=True)
    default_sender_email = models.EmailField(blank=True)
    default_reply_to_email = models.EmailField(blank=True)

    # Mail engine — admin/owner only
    backend = models.CharField(max_length=20, choices=BACKEND_CHOICES, default='smtp')
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.PositiveIntegerField(default=465)
    smtp_use_ssl = models.BooleanField(default=True)
    smtp_use_tls = models.BooleanField(default=False)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_from_email = models.EmailField(blank=True)

    class Meta:
        db_table = 'email_configurations'

    def __str__(self):
        return f"Email config for {self.organization.name}"


class ActivityLog(TimeStampedModel):
    """
    Lightweight audit trail for team management actions.
    """
    ACTION_CHOICES = [
        ('member_invited', 'Member Invited'),
        ('member_joined', 'Member Joined'),
        ('member_removed', 'Member Removed'),
        ('role_changed', 'Role Changed'),
        ('invitation_cancelled', 'Invitation Cancelled'),
        ('invitation_resent', 'Invitation Resent'),
        ('ownership_transferred', 'Ownership Transferred'),
        ('org_settings_updated', 'Organization Settings Updated'),
        # Platform-operator actions from the landlord console. Recorded against
        # the affected organization, with the operator in `user`, so a tenant
        # disputing a suspension can be answered from its own activity log.
        ('sending_suspended', 'Sending Suspended by Platform'),
        ('sending_resumed', 'Sending Resumed by Platform'),
        ('account_suspended', 'Account Suspended by Platform'),
        ('account_restored', 'Account Restored by Platform'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_email = models.EmailField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'activity_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} by {self.user} at {self.created_at}"
