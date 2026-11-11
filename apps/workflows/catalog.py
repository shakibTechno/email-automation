"""
Every node type a workflow can contain, declared once.

There used to be three lists: the model's NODE_TYPE_CHOICES, the executor's
dispatch table, and NODE_TYPES in the frontend. They drifted, as three copies
of one fact always do — four node types shipped working in the backend and
were invisible in the builder, including two pop-up triggers that nobody could
reach for a fortnight. This module is the single declaration; the model's
choices, the catalogue endpoint the palette renders from, and the reference
resolver used by import and AI generation are all derived from it.

Follows apps/contacts/fields.py, which exists for the same reason.

`config_fields` is what makes that possible. A node's configuration is declared
rather than hand-coded, so:

  * the builder can render a form for a simple node without a bespoke panel
  * import and AI generation know which config values name another object
    (`asset=`), which is exactly what has to be re-pointed when a workflow
    moves between accounts
  * a config key that references a tenant-owned object cannot be added without
    saying so, which is the failure that would leak one account's tags into
    another's workflow

Nodes whose configuration is genuinely bespoke — a pipeline that filters the
stage list beside it — keep their hand-written panel. `ui='custom'` says so.
"""
from dataclasses import dataclass, field as dataclass_field

# ─────────────────────────────────────────────────────────────── asset kinds
# What a config value can point at. The resolver maps these to a queryset and
# a display field; adding a kind here without teaching the resolver about it
# fails loudly in its tests rather than silently importing a dangling id.
ASSET_TAG = 'tag'
ASSET_EMAIL_TEMPLATE = 'email_template'
ASSET_FORM = 'form'
ASSET_SEGMENT = 'segment'
ASSET_POPUP = 'popup'
ASSET_PIPELINE = 'pipeline'
ASSET_STAGE = 'stage'
ASSET_USER = 'user'
ASSET_SEQUENCE = 'sequence'
ASSET_WORKFLOW = 'workflow'

ASSET_KINDS = frozenset({
    ASSET_TAG, ASSET_EMAIL_TEMPLATE, ASSET_FORM, ASSET_SEGMENT, ASSET_POPUP,
    ASSET_PIPELINE, ASSET_STAGE, ASSET_USER, ASSET_SEQUENCE, ASSET_WORKFLOW,
})

TRIGGER = 'trigger'
ACTION = 'action'
CONDITION = 'condition'


@dataclass(frozen=True)
class ConfigField:
    """One configurable value on a node."""

    key: str
    label: str
    # text | textarea | number | boolean | select | asset | duration | rules
    type: str = 'text'
    # Set when type == 'asset': which kind of object this id names.
    asset: str = ''
    # Set when type == 'select'.
    options: tuple = ()
    required: bool = False
    default: object = None
    help: str = ''
    # Only shown when another field has one of these values, e.g.
    # depends_on=('field', ('stage',)). The generic renderer honours it; it is
    # advisory for custom panels.
    depends_on: tuple = ()

    def __post_init__(self):
        if self.type == 'asset' and self.asset not in ASSET_KINDS:
            raise ValueError(
                f'{self.key}: asset field must name a known kind, got {self.asset!r}'
            )


@dataclass(frozen=True)
class NodeSpec:
    """One node type: what it is called, what it needs, and how it is drawn."""

    type: str
    category: str
    label: str
    description: str
    icon: str
    config_fields: tuple = ()
    # 'auto' renders from config_fields; 'custom' means a hand-written panel
    # owns it and the generic renderer must not try.
    ui: str = 'auto'
    # Trigger only: this one is polled by a periodic task rather than fired by
    # a signal, so a workflow using it is not broken by having no call site.
    scheduled: bool = False
    # How many outgoing branches, and what they are called. A node with more
    # than one needs an edge per branch.
    branches: tuple = ('default',)
    # Terminal nodes end the contact's run; nothing after them executes.
    terminal: bool = False

    @property
    def asset_fields(self):
        """The config fields that name another object."""
        return tuple(f for f in self.config_fields if f.type == 'asset')


def _f(key, label, type_='text', **kwargs):
    return ConfigField(key=key, label=label, type=type_, **kwargs)


# ──────────────────────────────────────────────────────────────── the catalogue

NODE_SPECS = (
    # ─────────────────────────────────────────────────────────────── triggers
    NodeSpec(
        'trigger_form_submission', TRIGGER, 'Form Submission',
        'When someone submits one of your forms', 'FileText',
        config_fields=(
            _f('form_id', 'Form', 'asset', asset=ASSET_FORM,
               help='Leave empty for any form.'),
        ),
    ),
    NodeSpec(
        'trigger_tag_added', TRIGGER, 'Tag Added',
        'When a tag is applied to a contact', 'Tag',
        config_fields=(
            _f('tag_id', 'Tag', 'asset', asset=ASSET_TAG, required=True),
        ),
    ),
    NodeSpec(
        'trigger_tag_removed', TRIGGER, 'Tag Removed',
        'When a tag is taken off a contact', 'TagMinus',
        config_fields=(
            _f('tag_id', 'Tag', 'asset', asset=ASSET_TAG, required=True),
        ),
    ),
    NodeSpec(
        'trigger_contact_created', TRIGGER, 'Contact Created',
        'When a new contact is added, however they arrive', 'UserPlus',
    ),
    NodeSpec(
        'trigger_contact_field_changed', TRIGGER, 'Field Changed',
        'When a contact field is given a new value', 'PencilLine',
        config_fields=(
            _f('field', 'Field', help='Leave empty for any field.'),
            _f('to_value', 'Changed to',
               help='Leave empty to fire on any new value.'),
        ),
    ),
    NodeSpec(
        'trigger_email_opened', TRIGGER, 'Email Opened',
        'When a contact opens a campaign email', 'MailOpen',
    ),
    NodeSpec(
        'trigger_email_clicked', TRIGGER, 'Email Clicked',
        'When a contact clicks a link in a campaign email', 'MousePointerClick',
    ),
    NodeSpec(
        'trigger_email_bounced', TRIGGER, 'Email Bounced',
        'When mail to a contact bounces', 'MailWarning',
        config_fields=(
            _f('bounce_type', 'Bounce type', 'select',
               options=(('any', 'Any'), ('hard', 'Hard only'), ('soft', 'Soft only')),
               default='any'),
        ),
    ),
    NodeSpec(
        'trigger_email_unsubscribed', TRIGGER, 'Unsubscribed',
        'When a contact opts out of your mail', 'MailX',
    ),
    NodeSpec(
        'trigger_popup_shown', TRIGGER, 'Pop-up Shown',
        'When a pop-up is displayed to a known contact', 'Maximize2',
        config_fields=(
            _f('popup_id', 'Pop-up', 'asset', asset=ASSET_POPUP,
               help='Leave empty for any pop-up.'),
        ),
    ),
    NodeSpec(
        'trigger_popup_clicked', TRIGGER, 'Pop-up Clicked',
        'When a contact clicks a pop-up call to action', 'MousePointerClick',
        config_fields=(
            _f('popup_id', 'Pop-up', 'asset', asset=ASSET_POPUP,
               help='Leave empty for any pop-up.'),
        ),
    ),
    NodeSpec(
        'trigger_page_visited', TRIGGER, 'Page Visited',
        'When a known contact views a page on your site', 'Globe',
        config_fields=(
            _f('path', 'Path', required=True,
               help='/pricing, or /blog/* to match everything below it.'),
            _f('times', 'How many visits', 'number', default=1,
               help='Fires once the contact has reached this many visits to '
                    'that page. Needs the tracking snippet installed.'),
        ),
    ),
    NodeSpec(
        'trigger_segment_entered', TRIGGER, 'Entered Segment',
        'When a contact starts matching a segment', 'UsersRound',
        config_fields=(
            _f('segment_id', 'Segment', 'asset', asset=ASSET_SEGMENT, required=True),
        ),
        scheduled=True,
    ),
    NodeSpec(
        'trigger_segment_left', TRIGGER, 'Left Segment',
        'When a contact stops matching a segment', 'UserRoundMinus',
        config_fields=(
            _f('segment_id', 'Segment', 'asset', asset=ASSET_SEGMENT, required=True),
        ),
        scheduled=True,
    ),
    NodeSpec(
        'trigger_lead_score_threshold', TRIGGER, 'Lead Score Reached',
        'When a contact crosses a score you choose', 'Gauge',
        config_fields=(
            _f('threshold', 'Score', 'number', required=True, default=50),
            _f('direction', 'Direction', 'select',
               options=(('above', 'Rises above'), ('below', 'Falls below')),
               default='above'),
        ),
    ),
    NodeSpec(
        'trigger_date_field', TRIGGER, 'Date Reached',
        'On a date held on the contact, such as a birthday', 'Calendar',
        config_fields=(
            _f('field', 'Date field', required=True, default='date_of_birth'),
            _f('offset_days', 'Days before or after', 'number', default=0,
               help='-7 is a week before; 0 is on the day.'),
            _f('recurring', 'Every year', 'boolean', default=True,
               help='Off means only the exact date, once.'),
        ),
        scheduled=True,
    ),
    NodeSpec(
        'trigger_deal_created', TRIGGER, 'Deal Created',
        'When a deal is opened for a contact', 'Briefcase',
        config_fields=(
            _f('pipeline_id', 'Pipeline', 'asset', asset=ASSET_PIPELINE,
               help='Leave empty for any pipeline.'),
        ),
    ),
    NodeSpec(
        'trigger_deal_stage_changed', TRIGGER, 'Deal Stage Changed',
        'When a deal moves to a particular stage', 'GitPullRequestArrow',
        config_fields=(
            _f('pipeline_id', 'Pipeline', 'asset', asset=ASSET_PIPELINE),
            _f('stage_id', 'Stage', 'asset', asset=ASSET_STAGE,
               depends_on=('pipeline_id', ()),
               help='Leave empty for any stage.'),
        ),
        ui='custom',
    ),
    NodeSpec(
        'trigger_deal_won', TRIGGER, 'Deal Won',
        'When a deal is marked won', 'Trophy',
    ),
    NodeSpec(
        'trigger_deal_lost', TRIGGER, 'Deal Lost',
        'When a deal is marked lost', 'CircleSlash',
    ),
    NodeSpec(
        'trigger_sequence_completed', TRIGGER, 'Sequence Finished',
        'When a contact reaches the end of a sequence', 'ListChecks',
        config_fields=(
            _f('sequence_id', 'Sequence', 'asset', asset=ASSET_SEQUENCE,
               help='Leave empty for any sequence.'),
        ),
    ),
    NodeSpec(
        'trigger_task_completed', TRIGGER, 'Task Completed',
        'When a sales task on the contact is marked done', 'CheckCircle2',
    ),
    NodeSpec(
        'trigger_webhook_received', TRIGGER, 'Webhook Received',
        'When another system posts to this workflow’s own URL', 'Webhook',
        config_fields=(
            _f('match_by', 'Find the contact by', 'select',
               options=(('email', 'Email address'), ('external_id', 'External ID')),
               default='email'),
            _f('create_missing', 'Create the contact if unknown', 'boolean',
               default=False),
        ),
        ui='custom',
    ),

    # ──────────────────────────────────────────────────────────────── actions
    NodeSpec(
        'action_send_email', ACTION, 'Send Email',
        'Send one of your templates to the contact', 'Mail',
        config_fields=(
            _f('template_id', 'Template', 'asset', asset=ASSET_EMAIL_TEMPLATE,
               required=True),
            _f('subject', 'Subject override',
               help='Leave empty to use the template’s own subject.'),
        ),
        ui='custom',
    ),
    NodeSpec(
        'action_wait', ACTION, 'Wait',
        'Hold the contact here for a while', 'Clock',
        config_fields=(
            _f('duration', 'Wait for', 'duration', required=True, default=1),
            _f('unit', 'Unit', 'select',
               options=(('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')),
               default='days'),
        ),
    ),
    NodeSpec(
        'action_wait_until', ACTION, 'Wait Until',
        'Hold until something becomes true, or give up', 'Hourglass',
        config_fields=(
            _f('rules', 'Wait for', 'rules', required=True),
            _f('timeout_hours', 'Give up after (hours)', 'number', default=72,
               help='The contact then takes the timeout branch.'),
        ),
        branches=('met', 'timeout'),
        ui='custom',
    ),
    NodeSpec(
        'action_add_tag', ACTION, 'Add Tag',
        'Apply a tag to the contact', 'TagPlus',
        config_fields=(
            _f('tag_id', 'Tag', 'asset', asset=ASSET_TAG, required=True),
        ),
    ),
    NodeSpec(
        'action_remove_tag', ACTION, 'Remove Tag',
        'Take a tag off the contact', 'TagMinus',
        config_fields=(
            _f('tag_id', 'Tag', 'asset', asset=ASSET_TAG, required=True),
        ),
    ),
    NodeSpec(
        'action_update_contact', ACTION, 'Update Contact',
        'Set a field on the contact', 'UserCog',
        config_fields=(
            _f('field', 'Field', required=True),
            _f('value', 'Value'),
        ),
        ui='custom',
    ),
    NodeSpec(
        'action_assign_contact', ACTION, 'Assign Owner',
        'Give the contact to a team member', 'UserCheck',
        config_fields=(
            _f('user_id', 'Team member', 'asset', asset=ASSET_USER, required=True),
        ),
    ),
    NodeSpec(
        'action_add_to_segment', ACTION, 'Add to Segment',
        'Put the contact in a static segment', 'UsersRound',
        config_fields=(
            _f('segment_id', 'Segment', 'asset', asset=ASSET_SEGMENT, required=True,
               help='Static segments only — a dynamic one decides its own members.'),
        ),
    ),
    NodeSpec(
        'action_remove_from_segment', ACTION, 'Remove from Segment',
        'Take the contact out of a static segment', 'UserRoundMinus',
        config_fields=(
            _f('segment_id', 'Segment', 'asset', asset=ASSET_SEGMENT, required=True),
        ),
    ),
    NodeSpec(
        'action_enroll_sequence', ACTION, 'Start Sequence',
        'Enrol the contact in a drip sequence', 'ListChecks',
        config_fields=(
            _f('sequence_id', 'Sequence', 'asset', asset=ASSET_SEQUENCE, required=True),
        ),
    ),
    NodeSpec(
        'action_remove_sequence', ACTION, 'Stop Sequence',
        'Take the contact out of a sequence', 'ListX',
        config_fields=(
            _f('sequence_id', 'Sequence', 'asset', asset=ASSET_SEQUENCE, required=True),
        ),
    ),
    NodeSpec(
        'action_enroll_workflow', ACTION, 'Start Another Workflow',
        'Hand the contact to a different workflow', 'Workflow',
        config_fields=(
            _f('workflow_id', 'Workflow', 'asset', asset=ASSET_WORKFLOW, required=True),
        ),
    ),
    NodeSpec(
        'action_remove_from_workflow', ACTION, 'Stop Another Workflow',
        'Cancel the contact’s run of another workflow', 'XOctagon',
        config_fields=(
            _f('workflow_id', 'Workflow', 'asset', asset=ASSET_WORKFLOW, required=True),
        ),
    ),
    NodeSpec(
        'action_update_lead_score', ACTION, 'Change Lead Score',
        'Add to or subtract from the contact’s score', 'Gauge',
        config_fields=(
            _f('operation', 'Operation', 'select',
               options=(('add', 'Add'), ('subtract', 'Subtract'), ('set', 'Set to')),
               default='add'),
            _f('points', 'Points', 'number', required=True, default=10),
        ),
    ),
    NodeSpec(
        'action_create_deal', ACTION, 'Create Deal',
        'Open a deal for the contact', 'Briefcase',
        config_fields=(
            _f('pipeline_id', 'Pipeline', 'asset', asset=ASSET_PIPELINE, required=True),
            _f('stage_id', 'Stage', 'asset', asset=ASSET_STAGE,
               help='Leave empty for the first stage.'),
            _f('title', 'Deal title',
               help='Leave empty to name it after the contact.'),
            _f('value', 'Value', 'number'),
        ),
        ui='custom',
    ),
    NodeSpec(
        'action_update_deal', ACTION, 'Update Deal',
        'Change the deal that started this workflow', 'PencilLine',
        config_fields=(
            _f('field', 'Field', 'select',
               options=(('stage', 'Stage'), ('status', 'Status'), ('value', 'Value')),
               required=True, default='stage'),
            _f('stage_id', 'Stage', 'asset', asset=ASSET_STAGE,
               depends_on=('field', ('stage',))),
            _f('value', 'Value'),
        ),
        ui='custom',
    ),
    NodeSpec(
        'action_create_task', ACTION, 'Create Task',
        'Give someone on the team something to do', 'CheckSquare',
        config_fields=(
            _f('title', 'Title', required=True),
            _f('description', 'Details', 'textarea'),
            _f('assigned_to', 'Assign to', 'asset', asset=ASSET_USER),
            _f('priority', 'Priority', 'select',
               options=(('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
                        ('urgent', 'Urgent')),
               default='medium'),
            _f('due_in_days', 'Due in (days)', 'number', default=1),
        ),
    ),
    NodeSpec(
        'action_add_note', ACTION, 'Add Note',
        'Record a note against the contact', 'StickyNote',
        config_fields=(
            _f('note', 'Note', 'textarea', required=True),
        ),
    ),
    NodeSpec(
        'action_notify_team', ACTION, 'Notify the Team',
        'Email someone internally about this contact', 'BellRing',
        config_fields=(
            _f('user_id', 'Team member', 'asset', asset=ASSET_USER,
               help='Leave empty to use the address below.'),
            _f('email', 'Or an address'),
            _f('subject', 'Subject', required=True),
            _f('message', 'Message', 'textarea'),
        ),
    ),
    NodeSpec(
        'action_unsubscribe', ACTION, 'Unsubscribe',
        'Opt the contact out of marketing mail', 'MailX',
        config_fields=(
            _f('reason', 'Reason', help='Recorded against the contact.'),
        ),
    ),
    NodeSpec(
        'action_webhook', ACTION, 'Webhook',
        'Post the contact to an external URL', 'Webhook',
        config_fields=(
            _f('url', 'URL', required=True),
            _f('method', 'Method', 'select',
               options=(('POST', 'POST'), ('PUT', 'PUT')), default='POST'),
            _f('headers', 'Headers', 'textarea',
               help='One per line, as Name: value.'),
        ),
        ui='custom',
    ),
    NodeSpec(
        'action_goal', ACTION, 'Goal',
        'Mark this as what the workflow was for', 'Target',
        config_fields=(
            _f('description', 'What was achieved'),
        ),
    ),
    NodeSpec(
        'action_end_flow', ACTION, 'End',
        'Finish the contact’s run here', 'Square',
        terminal=True,
    ),

    # ────────────────────────────────────────────────────────────────── logic
    NodeSpec(
        'condition_if_else', CONDITION, 'If / Else',
        'Send contacts down one of two paths', 'GitBranch',
        config_fields=(
            _f('rules', 'Rules', 'rules', required=True),
            _f('logic', 'Match', 'select',
               options=(('all', 'All of them'), ('any', 'Any of them')),
               default='all'),
        ),
        branches=('true', 'false'),
        ui='custom',
    ),
    NodeSpec(
        'condition_switch', CONDITION, 'Split by Rule',
        'Several named paths, first match wins', 'GitFork',
        config_fields=(
            _f('branches', 'Paths', 'rules', required=True,
               help='Each path has a name and its own rules. Anyone matching '
                    'none of them takes the fallback.'),
        ),
        branches=('fallback',),  # the rest are named by the config
        ui='custom',
    ),
    NodeSpec(
        'condition_split_test', CONDITION, 'A/B Split',
        'Divide contacts by percentage to compare two paths', 'Split',
        config_fields=(
            _f('percent_a', 'Share down path A (%)', 'number', default=50),
        ),
        branches=('a', 'b'),
    ),
)


# ──────────────────────────────────────────── rule fields the executor knows
# What a condition can test *beyond* a contact's own properties.
#
# Contact properties are not listed here on purpose: they come from
# apps/segments field definitions, which is what the executor actually
# evaluates them against, so a workflow condition and a segment rule cannot
# mean different things. These are the workflow-only ones -- things the
# contact *did*, which a segment has no concept of.
#
# Declared here rather than in the executor and again in the builder, because
# that pair is exactly how the node-type lists drifted.
BEHAVIOUR_RULE_FIELDS = (
    {
        'field': 'event.email_opened',
        'label': 'Opened an email in this workflow',
        'type': 'behaviour',
        'needs_value': False,
    },
    {
        'field': 'event.email_clicked',
        'label': 'Clicked an email in this workflow',
        'type': 'behaviour',
        'needs_value': False,
    },
    {
        'field': 'event.page_visited',
        'label': 'Visited a page',
        'type': 'behaviour',
        'needs_value': True,
        'value_label': 'Path, e.g. /pricing or /blog/*',
    },
    {
        'field': 'event.form_submitted',
        'label': 'Submitted a form',
        'type': 'behaviour',
        'needs_value': True,
        'value_asset': ASSET_FORM,
        'value_label': 'Any form unless you choose one',
    },
    {
        'field': 'in_segment',
        'label': 'Is in a segment',
        'type': 'behaviour',
        'needs_value': True,
        'value_asset': ASSET_SEGMENT,
    },
    {
        'field': 'deal.in_stage',
        'label': 'Has a deal in a stage',
        'type': 'behaviour',
        'needs_value': True,
        'value_asset': ASSET_STAGE,
    },
)

# Every behaviour rule answers yes or no, so these are the only two operators.
BEHAVIOUR_OPERATORS = (
    {'value': 'is_true', 'label': 'is true'},
    {'value': 'is_false', 'label': 'is not true'},
)

BEHAVIOUR_FIELD_NAMES = tuple(f['field'] for f in BEHAVIOUR_RULE_FIELDS)

# ───────────────────────────────────────────────────────────────── lookups

BY_TYPE = {spec.type: spec for spec in NODE_SPECS}

# What the model stores. Derived, so a node type cannot exist in one and not
# the other.
NODE_TYPE_CHOICES = [(spec.type, spec.label) for spec in NODE_SPECS]

TRIGGER_TYPES = frozenset(s.type for s in NODE_SPECS if s.category == TRIGGER)
ACTION_TYPES = frozenset(s.type for s in NODE_SPECS if s.category == ACTION)
CONDITION_TYPES = frozenset(s.type for s in NODE_SPECS if s.category == CONDITION)
TERMINAL_TYPES = frozenset(s.type for s in NODE_SPECS if s.terminal)
SCHEDULED_TRIGGERS = frozenset(s.type for s in NODE_SPECS if s.scheduled)


def spec_for(node_type):
    """The spec, or None for a node type this version does not know."""
    return BY_TYPE.get(node_type)


def exists(node_type):
    return node_type in BY_TYPE


def asset_fields_for(node_type):
    """
    The config keys on this node type that name another object.

    Import and AI generation both walk this rather than carrying their own
    list, so a new asset-referencing config field is handled by both the
    moment it is declared here.
    """
    spec = BY_TYPE.get(node_type)
    return spec.asset_fields if spec else ()


def branches_for(node_type):
    spec = BY_TYPE.get(node_type)
    return spec.branches if spec else ('default',)


def rule_fields():
    """Behaviour rule fields, as the rule editor consumes them."""
    return {
        'behaviour': [dict(field) for field in BEHAVIOUR_RULE_FIELDS],
        'behaviour_operators': [dict(op) for op in BEHAVIOUR_OPERATORS],
    }


def as_catalog():
    """
    The catalogue as the builder consumes it.

    Plain data: the palette, the generic config renderer and client-side
    validation all read this, so none of them keeps its own copy.
    """
    return [
        {
            'type': spec.type,
            'category': spec.category,
            'label': spec.label,
            'description': spec.description,
            'icon': spec.icon,
            'ui': spec.ui,
            'terminal': spec.terminal,
            'branches': list(spec.branches),
            'config_fields': [
                {
                    'key': f.key,
                    'label': f.label,
                    'type': f.type,
                    'asset': f.asset,
                    'options': [{'value': v, 'label': l} for v, l in f.options],
                    'required': f.required,
                    'default': f.default,
                    'help': f.help,
                    'depends_on': (
                        {'field': f.depends_on[0], 'values': list(f.depends_on[1])}
                        if f.depends_on else None
                    ),
                }
                for f in spec.config_fields
            ],
        }
        for spec in NODE_SPECS
    ]
