"""
Models for the CRM & Pipeline app.
"""
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Organization
from apps.contacts.models import Contact
import uuid


class Company(TimeStampedModel):
    """
    A company / account that contacts and deals belong to.
    """
    INDUSTRY_CHOICES = [
        ('technology', 'Technology'),
        ('financial_services', 'Financial Services'),
        ('healthcare', 'Healthcare'),
        ('retail', 'Retail'),
        ('manufacturing', 'Manufacturing'),
        ('real_estate', 'Real Estate'),
        ('education', 'Education'),
        ('media', 'Media & Entertainment'),
        ('consulting', 'Consulting'),
        ('other', 'Other'),
    ]

    SIZE_CHOICES = [
        ('1-10', '1–10 employees'),
        ('11-50', '11–50 employees'),
        ('51-200', '51–200 employees'),
        ('201-500', '201–500 employees'),
        ('501-1000', '501–1 000 employees'),
        ('1001+', '1 001+ employees'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='companies'
    )
    name = models.CharField(max_length=255)
    website = models.URLField(blank=True)
    domain = models.CharField(max_length=255, blank=True)
    industry = models.CharField(max_length=30, choices=INDUSTRY_CHOICES, blank=True)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, blank=True)
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_companies'
    )

    class Meta:
        db_table = 'crm_companies'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['domain']),
        ]

    def __str__(self):
        return self.name


class PipelineManager(models.Manager):
    """Manager for Pipeline model that excludes soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Pipeline(TimeStampedModel, SoftDeleteModel):
    """
    Sales pipeline containing stages for deal progression.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='pipelines'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    # Cached stats
    total_deals = models.PositiveIntegerField(default=0)
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_pipelines'
    )

    objects = PipelineManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'crm_pipelines'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Stage(TimeStampedModel):
    """
    A stage within a pipeline (e.g. Qualification, Proposal, Won).
    """
    STAGE_TYPE_CHOICES = [
        ('open', 'Open'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name='stages'
    )
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=7, default='#6366f1')
    position = models.PositiveIntegerField(default=0)
    stage_type = models.CharField(
        max_length=10,
        choices=STAGE_TYPE_CHOICES,
        default='open'
    )
    default_probability = models.PositiveIntegerField(default=50)

    class Meta:
        db_table = 'crm_stages'
        ordering = ['position']
        unique_together = [['pipeline', 'name']]

    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"


class DealManager(models.Manager):
    """Manager for Deal model that excludes soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Deal(TimeStampedModel, SoftDeleteModel):
    """
    A sales deal/opportunity within a pipeline stage.
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='deals'
    )
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name='deals'
    )
    stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        related_name='deals'
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='open'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )

    # Financial
    value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    probability = models.PositiveIntegerField(default=50)
    weighted_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Dates
    close_date = models.DateField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Win/Loss
    win_reason = models.CharField(max_length=255, blank=True)
    loss_reason = models.CharField(max_length=255, blank=True)

    # Company link
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deals'
    )

    # Ordering within stage
    position = models.PositiveIntegerField(default=0)

    # Deal rotting
    last_activity_at = models.DateTimeField(null=True, blank=True)
    is_rotting = models.BooleanField(default=False, db_index=True)
    rotting_threshold_days = models.PositiveIntegerField(default=30)

    # Relationships
    primary_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_deals'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_deals'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_deals'
    )

    objects = DealManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'crm_deals'
        ordering = ['position', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'pipeline']),
            models.Index(fields=['pipeline', 'stage', 'position']),
            models.Index(fields=['stage', 'status']),
            models.Index(fields=['close_date']),
            models.Index(fields=['primary_contact']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Auto-calculate weighted value
        self.weighted_value = (self.value * self.probability) / 100
        super().save(*args, **kwargs)


class DealContact(TimeStampedModel):
    """
    Many-to-many through model linking deals to contacts with roles.
    """
    ROLE_CHOICES = [
        ('primary', 'Primary'),
        ('decision_maker', 'Decision Maker'),
        ('influencer', 'Influencer'),
        ('champion', 'Champion'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='deal_contacts'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='deal_contacts'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='other'
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = 'crm_deal_contacts'
        unique_together = [['deal', 'contact']]

    def __str__(self):
        return f"{self.deal.title} - {self.contact.email} ({self.get_role_display()})"


class Activity(TimeStampedModel):
    """
    Sales activity (call, email, meeting, task, note) linked to deals/contacts.
    """
    ACTIVITY_TYPE_CHOICES = [
        ('call', 'Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('task', 'Task'),
        ('note', 'Note'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='crm_activities'
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='crm_activities'
    )

    activity_type = models.CharField(
        max_length=10,
        choices=ACTIVITY_TYPE_CHOICES,
        default='note'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text='Duration in minutes')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_crm_activities'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_crm_activities'
    )

    class Meta:
        db_table = 'crm_activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'activity_type']),
            models.Index(fields=['deal']),
            models.Index(fields=['contact']),
            models.Index(fields=['due_date', 'is_completed']),
            models.Index(fields=['assigned_to', 'is_completed']),
        ]

    def __str__(self):
        return f"{self.get_activity_type_display()}: {self.title}"


class CRMTask(TimeStampedModel):
    """
    Standalone task linked to a deal and/or contact.
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='crm_tasks'
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='crm_tasks'
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='todo'
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crm_tasks'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_crm_tasks'
    )

    class Meta:
        db_table = 'crm_tasks'
        ordering = ['due_date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['deal']),
            models.Index(fields=['contact']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]

    def __str__(self):
        return self.title


class DealStageHistory(TimeStampedModel):
    """
    Audit trail for deal stage movements.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='stage_history'
    )
    from_stage = models.ForeignKey(
        Stage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    to_stage = models.ForeignKey(
        Stage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    moved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    class Meta:
        db_table = 'crm_deal_stage_history'
        ordering = ['-created_at']

    def __str__(self):
        from_name = self.from_stage.name if self.from_stage else 'None'
        to_name = self.to_stage.name if self.to_stage else 'None'
        return f"{self.deal.title}: {from_name} -> {to_name}"
