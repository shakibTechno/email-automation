"""
Models for the AI Assistant app.

An organization connects its own LLM provider here (bring-your-own-key), and
generation runs are recorded as jobs so a long-running request can be polled
and so BYOK customers can see what their key is spending.
"""
import uuid

from django.db import models

from apps.core.models import TimeStampedModel


class AIConfiguration(TimeStampedModel):
    """
    One organization's LLM connection.

    Shaped to match `apps.email_config.models.EmailConfiguration`, which solves
    the same problem for sending providers: one row per organization, the
    secret on the model, masked by the serializer.
    """

    PROVIDER_ANTHROPIC = 'anthropic'
    PROVIDER_OPENAI = 'openai'
    PROVIDER_GOOGLE = 'google'
    PROVIDER_LOCAL = 'local'
    PROVIDER_CHOICES = [
        (PROVIDER_ANTHROPIC, 'Anthropic (Claude)'),
        (PROVIDER_OPENAI, 'OpenAI'),
        (PROVIDER_GOOGLE, 'Google (Gemini)'),
        (PROVIDER_LOCAL, 'Local server (llama.cpp / Ollama)'),
    ]

    #: Providers that are reached by address rather than by credential.
    SELF_HOSTED_PROVIDERS = (PROVIDER_LOCAL,)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='ai_configuration',
    )

    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_ANTHROPIC,
    )
    # Stored as-is and masked in the serializer, matching how
    # EmailConfiguration holds SMTP passwords and provider keys. See the note
    # in the plan: encrypting this one field alone would imply a protection the
    # neighbouring secrets do not have.
    api_key = models.CharField(max_length=512, blank=True)
    # Blank means "whatever the provider adapter considers current". For a
    # local server it means "whichever model that server has loaded".
    model = models.CharField(max_length=100, blank=True)
    # Only used by self-hosted providers, which are identified by where they
    # are rather than by a credential.
    base_url = models.URLField(max_length=500, blank=True)

    is_enabled = models.BooleanField(default=False)

    # Result of the last "Test connection", so the UI can show whether the key
    # is known-good rather than only whether one was typed.
    last_validated_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        db_table = 'ai_configurations'
        verbose_name = 'AI Configuration'
        verbose_name_plural = 'AI Configurations'

    def __str__(self):
        return f"AI config for {self.organization.name} ({self.provider})"

    @property
    def is_ready(self) -> bool:
        """
        Whether generation can actually be attempted.

        A hosted provider needs a key; a self-hosted one needs an address and
        usually has no authentication at all, so requiring a key there would
        make the feature permanently unreachable.
        """
        if not self.is_enabled:
            return False
        if self.provider in self.SELF_HOSTED_PROVIDERS:
            return bool(self.base_url)
        return bool(self.api_key)


class GenerationJob(TimeStampedModel):
    """
    One generation run, of whatever kind.

    Generation takes tens of seconds, so the request queues a job and the
    client polls it. The result is attached only on success, so a failed run
    leaves nothing half-made behind.

    The result is held in an explicit nullable FK per kind rather than a
    generic relation: deletes then cascade correctly and "which jobs produced
    this form" stays a normal query.
    """

    STATUS_QUEUED = 'queued'
    STATUS_RUNNING = 'running'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCEEDED, 'Succeeded'),
        (STATUS_FAILED, 'Failed'),
    ]

    KIND_LANDING_PAGE = 'landing_page'
    KIND_FORM = 'form'
    KIND_EMAIL_TEMPLATE = 'email_template'
    KIND_CAMPAIGN = 'campaign'
    KIND_CHOICES = [
        (KIND_LANDING_PAGE, 'Landing page'),
        (KIND_FORM, 'Form'),
        (KIND_EMAIL_TEMPLATE, 'Email template'),
        (KIND_CAMPAIGN, 'Campaign'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='page_generation_jobs',
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='page_generation_jobs',
    )

    # What was asked for.
    prompt = models.TextField()
    audience = models.CharField(max_length=255, blank=True)

    kind = models.CharField(
        max_length=20, choices=KIND_CHOICES, default=KIND_LANDING_PAGE,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)

    # Exactly one of these is set, decided by `kind`.
    landing_page = models.ForeignKey(
        'landing_pages.LandingPage',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='generation_jobs',
    )
    form = models.ForeignKey(
        'forms.Form',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='generation_jobs',
    )
    email_template = models.ForeignKey(
        'templates.EmailTemplate',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='generation_jobs',
    )
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='generation_jobs',
    )
    error_message = models.TextField(blank=True)
    # True when the sanitizer dropped something, so the UI can say the draft
    # was altered rather than silently differing from what the model wrote.
    was_sanitized = models.BooleanField(default=False)

    # What the run cost on the customer's own key.
    provider = models.CharField(max_length=20, blank=True)
    model = models.CharField(max_length=100, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_generation_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} generation {self.id} ({self.status})"

    @property
    def result(self):
        """The object this job produced, whatever kind it was."""
        return {
            self.KIND_LANDING_PAGE: self.landing_page,
            self.KIND_FORM: self.form,
            self.KIND_EMAIL_TEMPLATE: self.email_template,
            self.KIND_CAMPAIGN: self.campaign,
        }.get(self.kind)

    @property
    def result_id(self):
        result = self.result
        return str(result.id) if result else None
