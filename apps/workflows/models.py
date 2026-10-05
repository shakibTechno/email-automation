"""
Models for the Workflow Automation app.
"""
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Organization
from apps.contacts.models import Contact
import uuid


class WorkflowManager(models.Manager):
    """Manager for Workflow model that excludes soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Workflow(TimeStampedModel, SoftDeleteModel):
    """
    Workflow model for automation workflows.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='workflows'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # React Flow canvas state (nodes, edges, viewport)
    canvas_data = models.JSONField(default=dict, blank=True)

    # Goal tracking
    goal_node_id = models.CharField(max_length=100, blank=True)
    goal_description = models.CharField(max_length=255, blank=True)

    # Cached statistics
    contacts_entered = models.PositiveIntegerField(default=0)
    contacts_active = models.PositiveIntegerField(default=0)
    contacts_completed = models.PositiveIntegerField(default=0)
    contacts_goal_reached = models.PositiveIntegerField(default=0)

    # Timestamps
    activated_at = models.DateTimeField(null=True, blank=True)

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflows'
    )

    objects = WorkflowManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'workflows'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class WorkflowNode(TimeStampedModel):
    """
    Individual node within a workflow.
    Represents triggers, actions, conditions, and goals.
    """
    # Trigger types
    TRIGGER_FORM_SUBMISSION = 'trigger_form_submission'
    TRIGGER_TAG_ADDED = 'trigger_tag_added'
    TRIGGER_TAG_REMOVED = 'trigger_tag_removed'
    TRIGGER_CONTACT_CREATED = 'trigger_contact_created'
    TRIGGER_EMAIL_OPENED = 'trigger_email_opened'
    TRIGGER_EMAIL_CLICKED = 'trigger_email_clicked'
    TRIGGER_DATE_FIELD = 'trigger_date_field'

    # Action types
    ACTION_SEND_EMAIL = 'action_send_email'
    ACTION_ADD_TAG = 'action_add_tag'
    ACTION_REMOVE_TAG = 'action_remove_tag'
    ACTION_UPDATE_CONTACT = 'action_update_contact'
    ACTION_WAIT = 'action_wait'
    ACTION_WEBHOOK = 'action_webhook'
    ACTION_GOAL = 'action_goal'

    # Lead scoring trigger / action
    TRIGGER_LEAD_SCORE_THRESHOLD = 'trigger_lead_score_threshold'
    ACTION_UPDATE_LEAD_SCORE = 'action_update_lead_score'

    # CRM deal triggers / actions
    TRIGGER_DEAL_STAGE_CHANGED = 'trigger_deal_stage_changed'
    TRIGGER_DEAL_CREATED = 'trigger_deal_created'
    ACTION_UPDATE_DEAL = 'action_update_deal'

    # Logic types
    CONDITION_IF_ELSE = 'condition_if_else'

    NODE_TYPE_CHOICES = [
        # Triggers
        (TRIGGER_FORM_SUBMISSION, 'Form Submission'),
        (TRIGGER_TAG_ADDED, 'Tag Added'),
        (TRIGGER_TAG_REMOVED, 'Tag Removed'),
        (TRIGGER_CONTACT_CREATED, 'Contact Created'),
        (TRIGGER_EMAIL_OPENED, 'Email Opened'),
        (TRIGGER_EMAIL_CLICKED, 'Email Clicked'),
        (TRIGGER_DATE_FIELD, 'Date Field'),
        (TRIGGER_DEAL_STAGE_CHANGED, 'Deal Stage Changed'),
        (TRIGGER_DEAL_CREATED, 'Deal Created'),
        # Actions
        (ACTION_SEND_EMAIL, 'Send Email'),
        (ACTION_ADD_TAG, 'Add Tag'),
        (ACTION_REMOVE_TAG, 'Remove Tag'),
        (ACTION_UPDATE_CONTACT, 'Update Contact'),
        (ACTION_WAIT, 'Wait/Delay'),
        (ACTION_WEBHOOK, 'Webhook'),
        (ACTION_GOAL, 'Goal'),
        (ACTION_UPDATE_DEAL, 'Update Deal'),
        # Logic
        (CONDITION_IF_ELSE, 'If/Else Condition'),
        # Lead scoring
        (TRIGGER_LEAD_SCORE_THRESHOLD, 'Lead Score Threshold'),
        (ACTION_UPDATE_LEAD_SCORE, 'Update Lead Score'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='nodes'
    )
    node_type = models.CharField(
        max_length=50,
        choices=NODE_TYPE_CHOICES
    )

    # Position on canvas (React Flow coordinates)
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)

    # Node-specific configuration (JSON)
    config = models.JSONField(default=dict, blank=True)

    # Display label
    label = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'workflow_nodes'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['workflow', 'node_type']),
        ]

    def __str__(self):
        return f"{self.workflow.name} - {self.get_node_type_display()}"

    @property
    def is_trigger(self):
        """Check if this node is a trigger node."""
        return self.node_type.startswith('trigger_')

    @property
    def is_action(self):
        """Check if this node is an action node."""
        return self.node_type.startswith('action_')

    @property
    def is_condition(self):
        """Check if this node is a condition node."""
        return self.node_type.startswith('condition_')


class WorkflowEdge(TimeStampedModel):
    """
    Edge connecting two nodes in a workflow.
    """
    EDGE_TYPE_CHOICES = [
        ('default', 'Default'),
        ('true', 'True Branch'),
        ('false', 'False Branch'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='edges'
    )
    source_node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name='outgoing_edges'
    )
    target_node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name='incoming_edges'
    )
    edge_type = models.CharField(
        max_length=20,
        choices=EDGE_TYPE_CHOICES,
        default='default'
    )

    # React Flow handle identifiers
    source_handle = models.CharField(max_length=50, default='default')
    target_handle = models.CharField(max_length=50, default='default')

    class Meta:
        db_table = 'workflow_edges'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['workflow']),
            models.Index(fields=['source_node']),
            models.Index(fields=['target_node']),
        ]

    def __str__(self):
        return f"{self.source_node.label or self.source_node.node_type} -> {self.target_node.label or self.target_node.node_type}"


class WorkflowExecution(TimeStampedModel):
    """
    Tracks the execution of a workflow for a specific contact.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('waiting', 'Waiting'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='workflow_executions'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Current position in workflow
    current_node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_executions'
    )

    # For wait/delay nodes
    resume_at = models.DateTimeField(null=True, blank=True)

    # What triggered this execution
    trigger_data = models.JSONField(default=dict, blank=True)

    # Goal tracking
    goal_reached = models.BooleanField(default=False)
    goal_reached_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'workflow_executions'
        ordering = ['-started_at']
        # One active execution per contact per workflow
        unique_together = [['workflow', 'contact']]
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['contact']),
            models.Index(fields=['status']),
            models.Index(fields=['resume_at']),
        ]

    def __str__(self):
        return f"{self.workflow.name} - {self.contact.email} ({self.get_status_display()})"


class WorkflowExecutionStep(TimeStampedModel):
    """
    Records each step executed within a workflow execution.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.CASCADE,
        related_name='steps'
    )
    node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='execution_steps'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Data passed in/out of the node
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)

    # For condition nodes - which branch was taken
    branch_taken = models.CharField(max_length=20, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'workflow_execution_steps'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['execution']),
            models.Index(fields=['node']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        node_label = self.node.label if self.node else 'Unknown'
        return f"{self.execution} - {node_label} ({self.get_status_display()})"


class WorkflowTemplate(TimeStampedModel):
    """
    Reusable workflow templates.
    """
    CATEGORY_CHOICES = [
        ('welcome_series', 'Welcome Series'),
        ('lead_nurturing', 'Lead Nurturing'),
        ('re_engagement', 'Re-engagement'),
        ('onboarding', 'Onboarding'),
        ('promotional', 'Promotional'),
        ('custom', 'Custom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_templates'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='custom'
    )

    # Preview image
    thumbnail_url = models.URLField(blank=True)

    # Template content (nodes, edges, canvas settings)
    template_data = models.JSONField(default=dict, blank=True)

    # System vs user templates
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'workflow_templates'
        ordering = ['-is_system', '-usage_count', 'name']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['category']),
            models.Index(fields=['is_system', 'is_active']),
        ]

    def __str__(self):
        prefix = "[System] " if self.is_system else ""
        return f"{prefix}{self.name}"
