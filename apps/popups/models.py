"""
Website pop-ups.

A popup owns its content — title, image, call to action — and may *embed* one
of the organization's forms when it is there to capture something. That split
is why this is its own model rather than a kind of Form: an announcement bar
has no fields and records a click rather than a submission, and a Form has
nowhere to put a headline or an image.

What it is not is a second form engine. When a popup has a form, that form is
rendered by the same code that renders it anywhere else, with the same field
types, conditional logic, validation, contact mapping and downstream workflows.
"""
import uuid

from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


def default_design():
    """Colours, type and chrome. Mirrors the shape of Form.styling."""
    return {
        'backgroundColor': '#ffffff',
        'textColor': '#0f172a',
        'headingColor': '#0f172a',
        'fontFamily': 'Inter, system-ui, sans-serif',
        'borderRadius': '12px',
        'padding': '28px',
        'maxWidth': '440px',
        'backdrop': True,
        'backdropColor': 'rgba(15, 23, 42, 0.55)',
        'position': 'center',  # center | bottom_right | bottom_left | top
        'primaryButton': {
            'backgroundColor': '#4f46e5',
            'textColor': '#ffffff',
            'borderRadius': '8px',
            'fullWidth': False,
        },
        'closeButton': {
            'show': True,
            'color': '#64748b',
            # A popup that cannot be closed is a popup that gets the whole site
            # reported, so this is a delay before the control appears, never a
            # way to remove it.
            'delaySeconds': 0,
        },
        'image': {
            'position': 'top',  # top | left | background | none
            'height': '160px',
        },
    }


def default_triggers():
    """
    When it appears. One trigger, because two would need a precedence rule
    nobody would be able to predict from the UI.
    """
    return {
        'type': 'time',  # time | exit_intent | scroll | page_visit | click | inactivity
        'delaySeconds': 5,
        'scrollPercent': 50,
        'pageVisitCount': 2,
        'inactivitySeconds': 30,
        'clickSelector': '',
    }


def default_targeting():
    """
    Who sees it.

    Everything above `country` is decided in the visitor's browser from what
    the page already knows. `country` and `audience` cannot be: they cost the
    script one extra request before it may draw anything, so they are left
    empty and only the organizations that fill them pay for it.
    """
    return {
        'includeUrls': [],        # empty means every page
        'excludeUrls': [],
        'devices': ['desktop', 'mobile'],
        'visitorType': 'any',     # any | new | returning
        'referrers': [],          # substring match on document.referrer
        'utm': {},                # e.g. {'utm_campaign': 'spring'}
        'country': [],            # two-letter codes; needs GEOIP_PATH set
        'audience': {'segments': [], 'tags': [], 'contactFields': []},
    }


def default_frequency():
    """How often a visitor may see it again."""
    return {
        'mode': 'once_per_visitor',  # once_per_visitor | once_per_session |
                                     # every_n_days | every_visit
        'days': 7,
    }


class Popup(TimeStampedModel, SoftDeleteModel):
    TYPE_MODAL = 'modal'
    TYPE_SLIDE_IN = 'slide_in'
    TYPE_FLOATING_BAR = 'floating_bar'
    TYPE_FULL_SCREEN = 'full_screen'
    TYPE_CHOICES = [
        (TYPE_MODAL, 'Modal'),
        (TYPE_SLIDE_IN, 'Slide-in'),
        (TYPE_FLOATING_BAR, 'Floating bar'),
        (TYPE_FULL_SCREEN, 'Full screen'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_PUBLISHED = 'published'
    STATUS_PAUSED = 'paused'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_PAUSED, 'Paused'),
    ]
    # The only status the website script serves. Scheduled becomes published
    # when its start time arrives, by a task rather than by the script
    # guessing, so "why is it not showing" has one answer.
    LIVE_STATUSES = (STATUS_PUBLISHED,)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.CASCADE, related_name='popups',
    )
    name = models.CharField(max_length=255)
    popup_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_MODAL,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
    )

    # --- Content -----------------------------------------------------------
    title = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    image_url = models.URLField(max_length=1000, blank=True, default='')
    image_alt = models.CharField(max_length=255, blank=True, default='')

    cta_text = models.CharField(max_length=80, blank=True, default='')
    cta_url = models.URLField(max_length=1000, blank=True, default='')
    secondary_cta_text = models.CharField(max_length=80, blank=True, default='')
    secondary_cta_url = models.URLField(max_length=1000, blank=True, default='')

    # Optional on purpose: a popup with no form is an announcement, and that is
    # a thing marketers ask for. When it is set, the form renders inside and
    # everything a form submission already does still happens.
    form = models.ForeignKey(
        'forms.Form', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='popups',
    )

    # --- Behaviour ---------------------------------------------------------
    design = models.JSONField(default=default_design, blank=True)
    triggers = models.JSONField(default=default_triggers, blank=True)
    targeting = models.JSONField(default=default_targeting, blank=True)
    frequency = models.JSONField(default=default_frequency, blank=True)

    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    # --- Cached counters ---------------------------------------------------
    # Derived from TrackedEvent, kept here so a list of fifty popups is one
    # query rather than fifty aggregates.
    impression_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    conversion_count = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_popups',
    )

    class Meta:
        db_table = 'popups'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return self.name

    @property
    def conversion_rate(self):
        """
        Submissions (or clicks, with no form) per impression.

        Zero rather than None when nothing has been shown: a rate of "—" reads
        as broken, and the sample size is displayed beside it either way.
        """
        if not self.impression_count:
            return 0.0
        converted = self.conversion_count if self.form_id else self.click_count
        return round(converted / self.impression_count * 100, 2)

    def is_live(self, now=None):
        """Whether the script should serve this popup right now."""
        from django.utils import timezone

        now = now or timezone.now()
        if self.status not in self.LIVE_STATUSES or self.deleted_at:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at <= now:
            return False
        return True


class PopupTemplate(TimeStampedModel):
    """
    A starting point. Follows LandingPageTemplate: system templates have no
    organization, an organization's own saved ones do.
    """
    CATEGORY_CHOICES = [
        ('newsletter', 'Newsletter'),
        ('discount', 'Discount offer'),
        ('exit_offer', 'Exit offer'),
        ('lead_magnet', 'Lead magnet'),
        ('announcement', 'Announcement'),
        ('blank', 'Blank'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='popup_templates',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default='blank',
    )
    popup_type = models.CharField(
        max_length=20, choices=Popup.TYPE_CHOICES, default=Popup.TYPE_MODAL,
    )

    # The content and behaviour a new popup starts with. A template that only
    # sets colours saves nobody any time, so these carry copy and triggers too.
    content = models.JSONField(default=dict)
    design = models.JSONField(default=default_design)
    triggers = models.JSONField(default=default_triggers)
    # Whether a popup made from this one should capture. The form itself is
    # chosen by the marketer -- we cannot guess which of theirs it should be.
    wants_form = models.BooleanField(default=True)

    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'popup_templates'
        ordering = ['-usage_count', '-created_at']

    def __str__(self):
        return self.name
