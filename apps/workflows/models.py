"""
Models for the Workflow Automation app.
"""
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Organization
from apps.contacts.models import Contact
import uuid
from datetime import time

from . import catalog


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

    # ── Who may enter, and how often ─────────────────────────────────────────
    # Until this existed, start_execution refused a contact who had *any*
    # execution row, of any status. So a contact could enter a workflow once
    # in their lifetime: cart-abandon fired once per customer ever,
    # re-engagement could never re-engage, and testing a flow burned the
    # tester's own contact for good.
    REENTRY_ONCE = 'once'            # the old behaviour, kept for old flows
    REENTRY_ONE_AT_A_TIME = 'one_at_a_time'
    REENTRY_ALWAYS = 'always'
    REENTRY_CHOICES = [
        (REENTRY_ONCE, 'Once ever'),
        (REENTRY_ONE_AT_A_TIME, 'Again, but never twice at the same time'),
        (REENTRY_ALWAYS, 'Every time the trigger fires'),
    ]
    reentry = models.CharField(
        max_length=20, choices=REENTRY_CHOICES, default=REENTRY_ONE_AT_A_TIME,
    )
    # 0 means no cooldown. Applies to one_at_a_time and always.
    reentry_cooldown_days = models.PositiveIntegerField(default=0)

    # Optional gate on top of the trigger: the trigger says what happened,
    # this says who it counts for.
    entry_segment = models.ForeignKey(
        'segments.Segment', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='gated_workflows',
        help_text='Only contacts matching this segment may enter.',
    )

    # ── When mail may go out ─────────────────────────────────────────────────
    # A 24-hour wait otherwise lands at 03:00. Nothing is dropped: a step that
    # comes due outside these hours waits for the next open window.
    respect_quiet_hours = models.BooleanField(default=False)
    send_window_start = models.TimeField(default=time(9, 0))
    send_window_end = models.TimeField(default=time(18, 0))
    # 0=Monday .. 6=Sunday, matching Python's weekday(). Empty means every day.
    send_weekdays = models.JSONField(default=list, blank=True)

    # Goal tracking
    goal_node_id = models.CharField(max_length=100, blank=True)
    goal_description = models.CharField(max_length=255, blank=True)
    # A goal normally ends the run wherever the contact has got to — chasing
    # someone who already converted is the complaint this prevents. Off keeps
    # the old behaviour, where the goal was only a node you had to reach.
    exit_on_goal = models.BooleanField(default=True)
    # Rules that mean "this contact is done", checked before each step.
    goal_rules = models.JSONField(default=dict, blank=True)

    # Cached statistics
    contacts_entered = models.PositiveIntegerField(default=0)
    contacts_active = models.PositiveIntegerField(default=0)
    contacts_completed = models.PositiveIntegerField(default=0)
    contacts_goal_reached = models.PositiveIntegerField(default=0)

    # The path segment for this workflow's own inbound URL. Unguessable
    # because possessing it is the whole authorisation for starting a run.
    webhook_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

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
    # Node type names. The catalogue in catalog.py is the declaration — it
    # carries the label, the description, the icon and the config shape, and
    # NODE_TYPE_CHOICES below is derived from it. These constants exist so
    # call sites read as names rather than strings and stay greppable.

    # Triggers
    TRIGGER_FORM_SUBMISSION = 'trigger_form_submission'
    TRIGGER_TAG_ADDED = 'trigger_tag_added'
    TRIGGER_TAG_REMOVED = 'trigger_tag_removed'
    TRIGGER_CONTACT_CREATED = 'trigger_contact_created'
    TRIGGER_CONTACT_FIELD_CHANGED = 'trigger_contact_field_changed'
    TRIGGER_EMAIL_OPENED = 'trigger_email_opened'
    TRIGGER_EMAIL_CLICKED = 'trigger_email_clicked'
    TRIGGER_EMAIL_BOUNCED = 'trigger_email_bounced'
    TRIGGER_EMAIL_UNSUBSCRIBED = 'trigger_email_unsubscribed'
    TRIGGER_POPUP_SHOWN = 'trigger_popup_shown'
    TRIGGER_POPUP_CLICKED = 'trigger_popup_clicked'
    TRIGGER_PAGE_VISITED = 'trigger_page_visited'
    TRIGGER_SEGMENT_ENTERED = 'trigger_segment_entered'
    TRIGGER_SEGMENT_LEFT = 'trigger_segment_left'
    TRIGGER_LEAD_SCORE_THRESHOLD = 'trigger_lead_score_threshold'
    TRIGGER_DATE_FIELD = 'trigger_date_field'
    TRIGGER_DEAL_CREATED = 'trigger_deal_created'
    TRIGGER_DEAL_STAGE_CHANGED = 'trigger_deal_stage_changed'
    TRIGGER_DEAL_WON = 'trigger_deal_won'
    TRIGGER_DEAL_LOST = 'trigger_deal_lost'
    TRIGGER_SEQUENCE_COMPLETED = 'trigger_sequence_completed'
    TRIGGER_TASK_COMPLETED = 'trigger_task_completed'
    TRIGGER_WEBHOOK_RECEIVED = 'trigger_webhook_received'

    # Actions
    ACTION_SEND_EMAIL = 'action_send_email'
    ACTION_WAIT = 'action_wait'
    ACTION_WAIT_UNTIL = 'action_wait_until'
    ACTION_ADD_TAG = 'action_add_tag'
    ACTION_REMOVE_TAG = 'action_remove_tag'
    ACTION_UPDATE_CONTACT = 'action_update_contact'
    ACTION_ASSIGN_CONTACT = 'action_assign_contact'
    ACTION_ADD_TO_SEGMENT = 'action_add_to_segment'
    ACTION_REMOVE_FROM_SEGMENT = 'action_remove_from_segment'
    ACTION_ENROLL_SEQUENCE = 'action_enroll_sequence'
    ACTION_REMOVE_SEQUENCE = 'action_remove_sequence'
    ACTION_ENROLL_WORKFLOW = 'action_enroll_workflow'
    ACTION_REMOVE_FROM_WORKFLOW = 'action_remove_from_workflow'
    ACTION_UPDATE_LEAD_SCORE = 'action_update_lead_score'
    ACTION_CREATE_DEAL = 'action_create_deal'
    ACTION_UPDATE_DEAL = 'action_update_deal'
    ACTION_CREATE_TASK = 'action_create_task'
    ACTION_ADD_NOTE = 'action_add_note'
    ACTION_NOTIFY_TEAM = 'action_notify_team'
    ACTION_UNSUBSCRIBE = 'action_unsubscribe'
    ACTION_WEBHOOK = 'action_webhook'
    ACTION_GOAL = 'action_goal'
    ACTION_END_FLOW = 'action_end_flow'

    # Logic
    CONDITION_IF_ELSE = 'condition_if_else'
    CONDITION_SWITCH = 'condition_switch'
    CONDITION_SPLIT_TEST = 'condition_split_test'

    # Derived from the catalogue. There is no second list to keep in step.
    NODE_TYPE_CHOICES = catalog.NODE_TYPE_CHOICES

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
    # One per branch a node can offer. 'named' carries its label in
    # source_handle, which is how a switch node with four paths avoids four
    # more rows here.
    EDGE_TYPE_CHOICES = [
        ('default', 'Default'),
        ('true', 'True Branch'),
        ('false', 'False Branch'),
        ('a', 'Split A'),
        ('b', 'Split B'),
        ('met', 'Condition Met'),
        ('timeout', 'Timed Out'),
        ('fallback', 'Fallback'),
        ('named', 'Named Branch'),
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


class WorkflowSegmentWatch(TimeStampedModel):
    """
    Who was in a watched segment the last time we looked.

    "Entered a segment" and "left a segment" are changes, and a dynamic
    segment stores no membership to compare against -- only its cached count.
    This is that comparison point, one row per contact per watching node.

    Seeded from the segment's current membership when the workflow is
    activated, which is the whole point: without a baseline, switching on a
    workflow triggered by "entered segment" would treat every existing member
    as having just joined and mail all of them at once.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    node = models.ForeignKey(
        WorkflowNode, on_delete=models.CASCADE, related_name='segment_watch',
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='workflow_segment_watch',
    )

    class Meta:
        db_table = 'workflow_segment_watch'
        unique_together = [['node', 'contact']]
        indexes = [models.Index(fields=['node'])]

    def __str__(self):
        return f'{self.contact_id} in {self.node_id}'


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
    # Set only by Wait Until: when to stop waiting and take the timeout
    # branch. resume_at is when to look again; this is when to give up.
    wait_deadline = models.DateTimeField(null=True, blank=True)

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
        # There used to be unique_together on (workflow, contact) here, under
        # a comment claiming it allowed "one active execution per contact".
        # It did not: it covered every status, so a completed or cancelled run
        # barred that contact from the workflow for good. That constraint was
        # the re-entry rule, and no setting could override it.
        #
        # Re-entry is decided by WorkflowExecutionService.refusal_to_enter,
        # which can tell the three modes apart. Two triggers firing for the
        # same contact within milliseconds could still slip a duplicate run
        # past it.
        # shortcut: the re-entry check is not serialised, so a simultaneous
        # double trigger can start two runs; take a row lock on the workflow
        # if duplicate runs are ever observed.
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['contact']),
            models.Index(fields=['status']),
            models.Index(fields=['resume_at']),
            # What the dropped constraint was incidentally providing: the
            # lookup every entry decision makes.
            models.Index(fields=['workflow', 'contact', 'status']),
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
