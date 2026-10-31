"""
Models for the Forms & Lead Capture app.
"""
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Organization
from apps.contacts.models import Contact, Tag
import uuid
from apps.contacts import fields as contact_fields


class FormManager(models.Manager):
    """Manager for Form model that excludes soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


def default_styling():
    """Default styling configuration for forms."""
    return {
        'primaryColor': '#3b82f6',
        'backgroundColor': '#ffffff',
        'textColor': '#1f2937',
        'labelColor': '#374151',
        'borderColor': '#d1d5db',
        'errorColor': '#ef4444',
        'successColor': '#22c55e',
        'fontFamily': 'Inter, system-ui, sans-serif',
        'fontSize': '14px',
        'labelFontSize': '14px',
        'labelFontWeight': '500',
        'borderRadius': '6px',
        'fieldSpacing': '16px',
        'padding': '24px',
        'buttonStyle': {
            'backgroundColor': '#3b82f6',
            'textColor': '#ffffff',
            'hoverBackgroundColor': '#2563eb',
            'borderRadius': '6px',
            'fontSize': '14px',
            'fontWeight': '500',
            'padding': '10px 20px',
            'fullWidth': True,
        },
        'inputStyle': {
            'backgroundColor': '#ffffff',
            'borderWidth': '1px',
            'borderRadius': '6px',
            'padding': '10px 12px',
            'focusBorderColor': '#3b82f6',
            'focusRingColor': '#3b82f633',
        },
    }


def default_branding():
    """Default branding configuration for forms."""
    return {
        'logoUrl': '',
        'logoPosition': 'left',  # left, center, right
        'logoMaxHeight': '48px',
        'headerText': '',
        'headerFontSize': '24px',
        'headerFontWeight': '600',
        'headerAlignment': 'left',
        'footerText': '',
        'footerFontSize': '12px',
        'footerAlignment': 'center',
        'customCss': '',
        'showPoweredBy': True,
    }


def default_layout():
    """Default layout configuration for forms."""
    return {
        'formWidth': '100%',
        'maxWidth': '480px',
        'columns': 1,  # 1, 2, or 3 column layout
        'fieldGap': '16px',
        'rowGap': '16px',
        'alignment': 'left',  # left, center, right
    }


class Form(TimeStampedModel, SoftDeleteModel):
    """
    Form model for lead capture forms.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    # Popups are their own object now (apps/popups), and the popup types that
    # used to live here moved with them. A form is the thing embedded in a
    # page -- or inside a popup -- and nothing else.
    FORM_TYPE_CHOICES = [
        ('inline', 'Inline'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='forms'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='inactive'
    )
    form_type = models.CharField(
        max_length=20,
        choices=FORM_TYPE_CHOICES,
        default='inline'
    )

    # Form settings
    submit_button_text = models.CharField(max_length=50, default='Submit')
    success_message = models.TextField(default='Thank you for your submission!')
    redirect_url = models.URLField(blank=True)

    # GDPR
    show_gdpr_consent = models.BooleanField(default=False)
    gdpr_consent_text = models.TextField(
        default='I agree to receive communications and accept the privacy policy.'
    )

    # Design & Customization
    styling = models.JSONField(default=default_styling, blank=True)
    branding = models.JSONField(default=default_branding, blank=True)
    layout = models.JSONField(default=default_layout, blank=True)

    # Auto-assign tags to contacts on submission
    assign_tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='forms'
    )

    # Notifications (Phase 2)
    notification_emails = models.TextField(blank=True)

    # Cached count
    submission_count = models.PositiveIntegerField(default=0)

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='forms'
    )

    objects = FormManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'forms'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


def default_conditional_logic():
    """Default conditional logic (empty - field always visible)."""
    return {
        'enabled': False,
        'action': 'show',  # 'show' or 'hide'
        'logic': 'all',  # 'all' (AND) or 'any' (OR)
        'conditions': [],  # [{field_id, operator, value}]
    }


class FormField(TimeStampedModel):
    """
    Individual field within a form.
    """
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('dropdown', 'Dropdown'),
        ('checkbox', 'Checkbox'),
        ('radio', 'Radio'),
        ('textarea', 'Textarea'),
        ('date', 'Date'),
        ('number', 'Number'),
        ('url', 'URL'),
        ('hidden', 'Hidden'),
        ('section', 'Section Header'),
        ('divider', 'Divider'),
    ]

    WIDTH_CHOICES = [
        ('full', 'Full Width'),
        ('half', 'Half Width'),
        ('third', 'One Third'),
        ('two_thirds', 'Two Thirds'),
    ]

    # Generated from the contact field registry rather than listed here.
    # This was the fifth hand-maintained copy of "what fields a contact
    # has", and the reason a form could not capture anything added to the
    # model — the list simply never grew with it.
    CONTACT_FIELD_MAPPING_CHOICES = (
        [('', 'No mapping')]
        + contact_fields.writable_choices(contact_fields.FORM)
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(
        Form,
        on_delete=models.CASCADE,
        related_name='fields'
    )
    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default='text'
    )
    label = models.CharField(max_length=255)
    placeholder = models.CharField(max_length=255, blank=True)
    help_text = models.CharField(max_length=500, blank=True)
    is_required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)
    validation_rules = models.JSONField(default=dict, blank=True)
    order = models.PositiveIntegerField(default=0)
    contact_field_mapping = models.CharField(
        max_length=50,
        blank=True,
        choices=CONTACT_FIELD_MAPPING_CHOICES,
        default=''
    )

    # Layout options
    width = models.CharField(
        max_length=20,
        choices=WIDTH_CHOICES,
        default='full'
    )

    # Hidden field default value
    default_value = models.CharField(max_length=500, blank=True)

    # Section header styling
    section_description = models.TextField(blank=True)

    # Conditional logic
    conditional_logic = models.JSONField(default=default_conditional_logic, blank=True)

    # Advanced styling per field (optional overrides)
    custom_styling = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'form_fields'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['form', 'order']),
        ]

    def __str__(self):
        return f"{self.form.name} - {self.label} ({self.get_field_type_display()})"


class FormSubmission(TimeStampedModel):
    """
    Records a single form submission.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(
        Form,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='form_submissions'
    )
    data = models.JSONField(default=list)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    gdpr_consent_given = models.BooleanField(default=False)
    source_url = models.URLField(blank=True)

    class Meta:
        db_table = 'form_submissions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['form', 'created_at']),
            models.Index(fields=['contact']),
        ]

    def __str__(self):
        return f"Submission to {self.form.name} at {self.created_at}"
