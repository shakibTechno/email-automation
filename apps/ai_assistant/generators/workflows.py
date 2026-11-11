"""
Workflow generation.

Two rules decide whether this is useful or whether it joins the campaign
generator in being withdrawn.

**Ask for shape, never geometry.** The model returns an ordered list of steps.
Node ids, canvas coordinates, edge wiring and branch handles are all computed
here. A model asked for x/y produces a tangle, and a model asked for UUIDs
produces references to nothing — the same lesson as generators/forms.py, which
asks for design intent and derives the forty CSS values itself.

**Ground it in what the account actually has.** The prompt carries the
organization's real tag, template, form, segment and sequence names, and the
model is told to pick from them. Without that it invents "Welcome Email
Template", every node arrives pointing at nothing, and the feature feels
useless — which is the single most common reason AI builders get switched off.
The names come back as names and are resolved by the same AssetResolver an
import uses, so there is one definition of "find the thing called this".

Everything lands as a draft. A generated workflow has had no review, and one
that started mailing on creation would be indefensible.
"""
import logging

from apps.workflows import catalog
from apps.workflows.definition import FORMAT, VERSION, AssetResolver, build_from_definition

logger = logging.getLogger(__name__)

# What the model may choose from. Derived from the catalogue, minus the few
# that cannot be described in a sentence or need a canvas to make sense.
_EXCLUDED = {
    # Needs a URL from an external system that does not exist yet.
    'trigger_webhook_received',
    # Both need rule trees that are better built by hand than described.
    'condition_switch',
    'action_wait_until',
}

TRIGGER_CHOICES = sorted(catalog.TRIGGER_TYPES - _EXCLUDED)
STEP_CHOICES = sorted(
    (catalog.ACTION_TYPES | catalog.CONDITION_TYPES) - _EXCLUDED
)
# Branch steps may not branch again: one level of nesting covers nearly every
# real drip workflow, and recursion in a JSON schema is where providers start
# returning things that do not validate.
LEAF_CHOICES = sorted(catalog.ACTION_TYPES - _EXCLUDED - {'action_goal'})

SYSTEM_PROMPT = """You design marketing automation workflows.

You will be given a goal, and a list of the assets that already exist in this \
account: tags, email templates, forms, segments and sequences.

Rules:
- Refer to assets by their exact name from the lists you are given. Never \
invent a name. If the account has no suitable asset for a step, choose a \
different step.
- Build the smallest workflow that achieves the goal. Three to seven steps is \
usually right. A workflow with twelve steps is almost always worse than one \
with five.
- Put a wait before every follow-up email. Two emails with no delay between \
them is a mistake.
- Use a condition when the next step genuinely depends on what the contact \
did. Do not add a condition that both branches answer the same way.
- Leave a field as an empty string when it does not apply to that step type.
- Never write HTML, ids, coordinates or JSON inside a field value.
"""


def _step_properties(type_choices, *, with_branches):
    """One step's shape. Branch steps use the same shape minus the branches."""
    properties = {
        'type': {
            'type': 'string',
            'enum': type_choices,
            'description': 'Which kind of step this is.',
        },
        'label': {
            'type': 'string',
            'description': 'Short label shown on the step, 2-5 words.',
        },
        'template_name': {
            'type': 'string',
            'description': 'For a send-email step: the exact name of an email '
                           'template from the list. Empty otherwise.',
        },
        'tag_name': {
            'type': 'string',
            'description': 'For an add-tag or remove-tag step: the exact tag '
                           'name from the list. Empty otherwise.',
        },
        'segment_name': {
            'type': 'string',
            'description': 'For a segment step: the exact segment name from the '
                           'list. Empty otherwise.',
        },
        'sequence_name': {
            'type': 'string',
            'description': 'For a sequence step: the exact sequence name from '
                           'the list. Empty otherwise.',
        },
        'wait_amount': {
            'type': 'integer',
            'description': 'For a wait step: how long to wait. 0 otherwise.',
        },
        'wait_unit': {
            'type': 'string',
            'enum': ['minutes', 'hours', 'days'],
            'description': 'For a wait step: the unit of wait_amount.',
        },
        'points': {
            'type': 'integer',
            'description': 'For a lead-score step: how many points. 0 otherwise.',
        },
        'field': {
            'type': 'string',
            'description': 'For an update-contact step: the field to set, such '
                           'as lifecycle_stage. Empty otherwise.',
        },
        'value': {
            'type': 'string',
            'description': 'For an update-contact step: the value to set. '
                           'Empty otherwise.',
        },
        'text': {
            'type': 'string',
            'description': 'The body text for a note, an internal notification '
                           'or a task description. Empty otherwise.',
        },
        'subject': {
            'type': 'string',
            'description': 'For a notify or task step: its subject or title. '
                           'Empty otherwise.',
        },
        'condition': {
            'type': 'string',
            'enum': [
                '', 'opened_the_email', 'clicked_the_email',
                'visited_a_page', 'submitted_a_form', 'in_a_segment',
            ],
            'description': 'For a condition step: what is being tested. '
                           'Empty for every other step type.',
        },
    }
    required = sorted(properties)

    if with_branches:
        leaf_properties, leaf_required = _step_properties(
            LEAF_CHOICES, with_branches=False,
        )
        leaf = {
            'type': 'object',
            'additionalProperties': False,
            'properties': leaf_properties,
            'required': leaf_required,
        }
        properties['if_true'] = {
            'type': 'array', 'items': leaf,
            'description': 'For a condition step: the steps taken when it is '
                           'true. Empty array for every other step type.',
        }
        properties['if_false'] = {
            'type': 'array', 'items': leaf,
            'description': 'For a condition step: the steps taken when it is '
                           'false. Empty array for every other step type.',
        }
        required = sorted(properties)

    return properties, required


_STEP_PROPERTIES, _STEP_REQUIRED = _step_properties(STEP_CHOICES, with_branches=True)

SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['name', 'description', 'trigger', 'steps'],
    'properties': {
        'name': {
            'type': 'string',
            'description': 'Short internal name for the workflow, 2-5 words.',
        },
        'description': {
            'type': 'string',
            'description': 'One sentence saying what this workflow is for.',
        },
        'trigger': {
            'type': 'object',
            'additionalProperties': False,
            'required': [
                'type', 'form_name', 'tag_name', 'segment_name', 'path', 'field',
            ],
            'properties': {
                'type': {
                    'type': 'string',
                    'enum': TRIGGER_CHOICES,
                    'description': 'What starts the workflow.',
                },
                'form_name': {
                    'type': 'string',
                    'description': 'For a form trigger: the exact form name '
                                   'from the list. Empty otherwise.',
                },
                'tag_name': {
                    'type': 'string',
                    'description': 'For a tag trigger: the exact tag name from '
                                   'the list. Empty otherwise.',
                },
                'segment_name': {
                    'type': 'string',
                    'description': 'For a segment trigger: the exact segment '
                                   'name from the list. Empty otherwise.',
                },
                'path': {
                    'type': 'string',
                    'description': 'For a page-visited trigger: the path, such '
                                   'as /pricing. Empty otherwise.',
                },
                'field': {
                    'type': 'string',
                    'description': 'For a date trigger: the date field, such as '
                                   'date_of_birth. Empty otherwise.',
                },
            },
        },
        'steps': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'properties': _STEP_PROPERTIES,
                'required': _STEP_REQUIRED,
            },
        },
    },
}


# ──────────────────────────────────────────────────────────────── the prompt

def build_user_prompt(*, prompt: str, audience: str = '', organization=None) -> str:
    """
    The goal, plus the assets this account actually has.

    The asset lists are the whole reason a generated workflow is usable: a
    model with no inventory names plausible-sounding templates that do not
    exist, and every node arrives broken.
    """
    parts = [f'Goal: {prompt.strip()}']
    if audience:
        parts.append(f'Audience: {audience.strip()}')

    if organization is not None:
        for heading, names in _inventory(organization).items():
            parts.append(
                f'{heading} available in this account: '
                + (', '.join(f'"{name}"' for name in names) if names else '(none)')
            )
        parts.append(
            'Only use the names listed above. If a list says (none), do not '
            'use a step that needs one.'
        )
    return '\n\n'.join(parts)


def _inventory(organization, limit=40):
    """What this account has to build with."""
    from apps.contacts.models import Tag
    from apps.forms.models import Form
    from apps.segments.models import Segment
    from apps.sequences.models import EmailSequence
    from apps.templates.models import EmailTemplate

    def names(queryset, field='name'):
        return list(
            queryset.filter(organization=organization)
            .order_by('-created_at')
            .values_list(field, flat=True)[:limit]
        )

    return {
        'Email templates': names(EmailTemplate.objects),
        'Tags': names(Tag.objects),
        'Forms': names(Form.objects),
        'Segments': names(Segment.objects),
        'Sequences': names(EmailSequence.objects),
    }


# ─────────────────────────────────────────────────────────── payload → nodes

# Canvas geometry. The model never sees these.
_X_STEP = 0
_Y_STEP = 150
_BRANCH_DX = 280

_CONDITION_FIELDS = {
    'opened_the_email': ('event.email_opened', ''),
    'clicked_the_email': ('event.email_clicked', ''),
    'visited_a_page': ('event.page_visited', ''),
    'submitted_a_form': ('event.form_submitted', ''),
    'in_a_segment': ('in_segment', 'segment_name'),
}


def create(job, payload: dict):
    """Build the workflow, re-pointing every name at something real."""
    organization = job.organization
    resolver = AssetResolver(organization)

    nodes, edges = [], []
    counter = _Counter()

    trigger_id = _add_trigger(payload.get('trigger') or {}, nodes, counter, resolver)
    previous = trigger_id
    y = _Y_STEP

    for raw in (payload.get('steps') or [])[:20]:
        if not isinstance(raw, dict):
            continue
        step_type = raw.get('type')
        if not catalog.exists(step_type) or step_type in _EXCLUDED:
            continue

        y += _Y_STEP
        node_id = counter.next()
        nodes.append(_node(node_id, step_type, raw, 0, y, resolver))
        if step_type == 'condition_if_else' and not nodes[-1]['config'].get('rules'):
            # An empty rule list reads as "true" in the executor, so every
            # contact would go down one branch and the condition would look
            # ignored. Say so where someone will see it.
            nodes[-1]['label'] = (
                f"{nodes[-1]['label'] or 'Condition'} — needs setting up"[:100]
            )
        if previous:
            edges.append(_edge(previous, node_id))

        if step_type in catalog.CONDITION_TYPES:
            previous = _add_branches(raw, node_id, nodes, edges, counter, resolver, y)
            y += _Y_STEP * 2
        else:
            previous = node_id

    definition = {
        'format': FORMAT,
        'version': VERSION,
        'workflow': {
            'name': (payload.get('name') or 'Generated workflow')[:255],
            'description': payload.get('description') or '',
        },
        'canvas': {},
        'nodes': nodes,
        'edges': edges,
    }

    # The same builder templates and imports use. Node config already holds
    # real ids by this point, so nothing is left for it to resolve -- it is
    # here for the validation and the always-a-draft guarantee.
    workflow, report = build_from_definition(organization, definition, user=job.created_by)
    if resolver.unresolved:
        logger.info(
            'Generated workflow %s has %d step(s) the model named but this '
            'account does not have: %s',
            workflow.id, len(resolver.unresolved),
            ', '.join(sorted({item['name'] for item in resolver.unresolved})),
        )
    return workflow


class _Counter:
    """Stable node ids, so edges can name them before the rows exist."""

    def __init__(self):
        self._n = 0

    def next(self):
        self._n += 1
        return f'n{self._n}'


def _add_trigger(raw, nodes, counter, resolver):
    trigger_type = raw.get('type')
    if not catalog.exists(trigger_type) or trigger_type not in catalog.TRIGGER_TYPES:
        # Something has to start it, and a workflow with no trigger fails
        # validation. A new contact is the least surprising fallback.
        trigger_type = 'trigger_contact_created'

    node_id = counter.next()
    nodes.append(_node(node_id, trigger_type, raw, 0, 0, resolver))
    return node_id


def _add_branches(raw, condition_id, nodes, edges, counter, resolver, y):
    """
    Lay out the two sides of a condition and return where to continue.

    Both branches end on their own, deliberately: rejoining them would need a
    merge node the canvas does not have, and a workflow that quietly carries
    on down one branch is worse than one that stops.
    """
    for branch, dx in (('true', -_BRANCH_DX), ('false', _BRANCH_DX)):
        previous = condition_id
        branch_y = y
        steps = raw.get('if_true' if branch == 'true' else 'if_false') or []
        for leaf in steps[:5]:
            if not isinstance(leaf, dict):
                continue
            leaf_type = leaf.get('type')
            if not catalog.exists(leaf_type) or leaf_type not in catalog.ACTION_TYPES:
                continue
            branch_y += _Y_STEP
            node_id = counter.next()
            nodes.append(_node(node_id, leaf_type, leaf, dx, branch_y, resolver))
            edges.append(
                _edge(previous, node_id, branch if previous == condition_id else 'default')
            )
            previous = node_id
    return None


def _edge(source, target, branch='default'):
    return {
        'source_node_id': source,
        'target_node_id': target,
        'edge_type': branch,
        'source_handle': branch,
        'target_handle': 'default',
    }


def _node(node_id, node_type, raw, x, y, resolver):
    return {
        'id': node_id,
        'node_type': node_type,
        'label': (raw.get('label') or '')[:100],
        'position_x': x,
        'position_y': y,
        'config': _config(node_type, raw, resolver),
        'assets': {},
    }


def _config(node_type, raw, resolver):
    """
    Turn the model's names into the config a node actually takes.

    Driven by the catalogue's asset fields, so a node type that gains a
    reference is handled here without a change: the name slot is looked up by
    kind rather than by a per-node-type branch.
    """
    spec = catalog.spec_for(node_type)
    config = {}
    where = raw.get('label') or spec.label

    # Names the model may supply, by the kind of thing they name.
    supplied = {
        catalog.ASSET_EMAIL_TEMPLATE: raw.get('template_name'),
        catalog.ASSET_TAG: raw.get('tag_name'),
        catalog.ASSET_SEGMENT: raw.get('segment_name'),
        catalog.ASSET_SEQUENCE: raw.get('sequence_name'),
        catalog.ASSET_FORM: raw.get('form_name'),
    }

    for field in spec.asset_fields:
        name = (supplied.get(field.asset) or '').strip()
        if not name:
            continue
        resolved = resolver.by_name(field.asset, name, where=where)
        if resolved:
            config[field.key] = resolved

    # The plain values, per node type. Short and explicit beats clever here:
    # each of these is one line and says what it is.
    if node_type == 'action_wait':
        try:
            amount = max(1, int(raw.get('wait_amount') or 1))
        except (TypeError, ValueError):
            amount = 1
        config['duration'] = amount
        config['unit'] = (
            raw.get('wait_unit') if raw.get('wait_unit') in ('minutes', 'hours', 'days')
            else 'days'
        )
    elif node_type == 'action_update_lead_score':
        try:
            config['points'] = abs(int(raw.get('points') or 10))
        except (TypeError, ValueError):
            config['points'] = 10
        config['operation'] = 'add'
    elif node_type == 'action_update_contact':
        config['field'] = (raw.get('field') or '').strip()
        config['value'] = (raw.get('value') or '').strip()
    elif node_type == 'action_add_note':
        config['note'] = (raw.get('text') or '').strip()
    elif node_type == 'action_notify_team':
        config['subject'] = (raw.get('subject') or 'A contact needs attention')[:255]
        config['message'] = (raw.get('text') or '').strip()
    elif node_type == 'action_create_task':
        config['title'] = (raw.get('subject') or 'Follow up')[:255]
        config['description'] = (raw.get('text') or '').strip()
        config['priority'] = 'medium'
        config['due_in_days'] = 1
    elif node_type == 'action_goal':
        config['description'] = (raw.get('text') or raw.get('label') or '')[:255]
    elif node_type == 'condition_if_else':
        config.update(_condition_rules(raw, resolver, where))
    elif node_type == 'condition_split_test':
        config['percent_a'] = 50
    elif node_type == 'trigger_page_visited':
        config['path'] = (raw.get('path') or '').strip()
        config['times'] = 1
    elif node_type == 'trigger_date_field':
        config['field'] = (raw.get('field') or 'date_of_birth').strip()
        config['offset_days'] = 0
        config['recurring'] = True

    return config


def _condition_rules(raw, resolver, where):
    """The model's one-word condition turned into a rule the executor runs."""
    choice = (raw.get('condition') or '').strip()
    field, name_slot = _CONDITION_FIELDS.get(choice, ('', ''))
    if not field:
        # No testable condition came back. An empty rule list reads as "true"
        # in the executor, which would send every contact down one branch and
        # look like the condition was ignored -- so say so on the node.
        return {'rules': [], 'logic': 'all'}

    value = ''
    if name_slot:
        value = resolver.by_name(
            catalog.ASSET_SEGMENT, (raw.get(name_slot) or '').strip(), where=where,
        ) or ''

    return {
        'rules': [{'field': field, 'operator': 'is_true', 'value': value}],
        'logic': 'all',
    }
