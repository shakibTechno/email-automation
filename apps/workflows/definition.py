"""
A workflow as portable data, and the one builder that turns data into one.

Three things want to create a workflow from a description of it: a template,
an imported file, and the AI generator. They all come here. `create_from_template`
used to be the only one and wrote `node_type` and `config` straight through,
which is fine for a template we author and not fine for an uploaded file.

The hard part is not the shape, it is the **references**. A workflow's node
config is full of ids — tags, templates, forms, segments, pipelines, stages,
sequences, team members — and every one of them belongs to whoever exported it.
Carried across unchanged they are broken at best and another tenant's data at
worst. So an export records what each id was *called*, and an import re-points
it by name inside the importing account, reporting anything it could not place.

Which config keys hold references is not a list kept here: it comes from
catalog.asset_fields_for(), so a new asset-referencing field is handled by
import and by the generator the moment it is declared.
"""
import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from . import catalog
from .models import Workflow, WorkflowEdge, WorkflowNode

logger = logging.getLogger(__name__)

FORMAT = 'mailflow.workflow'
VERSION = 1

# An import is untrusted input sized by whoever wrote the file.
MAX_NODES = 200
MAX_EDGES = 400

# The workflow-level settings an export carries. Deliberately not everything:
# status, counters, timestamps and the webhook token describe this copy's
# history, not its design, and an import that restored them would claim
# another account's statistics.
PORTABLE_FIELDS = (
    'name', 'description', 'reentry', 'reentry_cooldown_days',
    'respect_quiet_hours', 'send_weekdays', 'exit_on_goal', 'goal_rules',
    'goal_description',
)


class DefinitionError(ValueError):
    """The payload is not a workflow this version can build."""


# ───────────────────────────────────────────────────────────────── resolving

class AssetResolver:
    """
    Turns a reference in an exported workflow into one this account owns.

    Tries the original id first, which makes an export/import inside the same
    account lossless, then the recorded name. Anything it cannot place is
    cleared and listed, so the workflow arrives as a draft with the gaps
    visible rather than silently pointing at nothing.
    """

    def __init__(self, organization):
        self.organization = organization
        self.unresolved = []
        self._cache = {}

    # kind -> (dotted model, field holding the display name)
    MODELS = {
        catalog.ASSET_TAG: ('contacts.Tag', 'name'),
        catalog.ASSET_EMAIL_TEMPLATE: ('templates.EmailTemplate', 'name'),
        catalog.ASSET_FORM: ('forms.Form', 'name'),
        catalog.ASSET_SEGMENT: ('segments.Segment', 'name'),
        catalog.ASSET_POPUP: ('popups.Popup', 'name'),
        catalog.ASSET_PIPELINE: ('crm.Pipeline', 'name'),
        catalog.ASSET_STAGE: ('crm.Stage', 'name'),
        catalog.ASSET_USER: ('accounts.User', 'email'),
        catalog.ASSET_SEQUENCE: ('sequences.EmailSequence', 'name'),
        catalog.ASSET_WORKFLOW: ('workflows.Workflow', 'name'),
    }

    def _queryset(self, kind):
        from django.apps import apps as django_apps

        dotted, _ = self.MODELS[kind]
        app_label, model_name = dotted.split('.')
        model = django_apps.get_model(app_label, model_name)

        if kind == catalog.ASSET_STAGE:
            # A stage has no organization of its own; it belongs to one
            # through its pipeline.
            return model.objects.filter(
                pipeline__organization=self.organization
            )
        return model.objects.filter(organization=self.organization)

    def resolve(self, kind, object_id, name, where=''):
        """
        The id to store, or None.

        `where` names the node for the report; a list of unplaced names with
        no indication of which step they came from is not actionable.
        """
        if kind not in self.MODELS:
            logger.error('No resolver for asset kind %r', kind)
            return None
        if not (object_id or name):
            return None

        cache_key = (kind, str(object_id or ''), (name or '').lower())
        if cache_key in self._cache:
            found = self._cache[cache_key]
        else:
            found = self._lookup(kind, object_id, name)
            self._cache[cache_key] = found

        if found is None:
            self.unresolved.append({
                'kind': kind,
                'name': name or str(object_id),
                'node': where,
            })
            return None
        return str(found)

    def _lookup(self, kind, object_id, name):
        queryset = self._queryset(kind)
        _, name_field = self.MODELS[kind]

        if object_id:
            # Same-account restore: the id is still right.
            try:
                match = (
                    queryset.filter(id=object_id)
                    .values_list('id', flat=True).first()
                )
            except (ValueError, TypeError, ValidationError):
                # Not a UUID at all — a hand-edited file. Fall through to the
                # name, which is the only thing left to go on.
                match = None
            if match:
                return match

        if name:
            return (
                queryset.filter(**{f'{name_field}__iexact': name})
                .values_list('id', flat=True)
                .first()
            )
        return None

    def by_name(self, kind, name, where=''):
        """Resolve from a name alone — what the AI generator has to work with."""
        return self.resolve(kind, None, name, where=where)


# ──────────────────────────────────────────────────────────────── exporting

def export_definition(workflow):
    """
    The workflow as portable data.

    Each node carries an `assets` sidecar naming what its config points at,
    which is what lets an import re-point it. `config` itself is untouched.
    """
    nodes = list(workflow.nodes.all())
    names = _asset_names(workflow, nodes)

    return {
        'format': FORMAT,
        'version': VERSION,
        'workflow': {
            field: _jsonable(getattr(workflow, field))
            for field in PORTABLE_FIELDS
        },
        'canvas': workflow.canvas_data or {},
        'nodes': [
            {
                'id': str(node.id),
                'node_type': node.node_type,
                'label': node.label,
                'position_x': node.position_x,
                'position_y': node.position_y,
                'config': node.config or {},
                'assets': names.get(str(node.id), {}),
            }
            for node in nodes
        ],
        'edges': [
            {
                'source_node_id': str(edge.source_node_id),
                'target_node_id': str(edge.target_node_id),
                'edge_type': edge.edge_type,
                'source_handle': edge.source_handle,
                'target_handle': edge.target_handle,
            }
            for edge in workflow.edges.all()
        ],
    }


def _asset_names(workflow, nodes):
    """
    `{node_id: {config_key: {kind, name}}}` for every reference in the flow.

    Looked up per kind in one query each rather than per node, so a fifty-node
    workflow does not become fifty queries.
    """
    wanted = {}
    for node in nodes:
        config = node.config or {}
        for field in catalog.asset_fields_for(node.node_type):
            value = config.get(field.key)
            if value:
                wanted.setdefault(field.asset, set()).add(str(value))

    resolver = AssetResolver(workflow.organization)
    lookup = {}
    for kind, ids in wanted.items():
        if kind not in AssetResolver.MODELS:
            continue
        _, name_field = AssetResolver.MODELS[kind]
        rows = resolver._queryset(kind).filter(id__in=ids).values_list(
            'id', name_field,
        )
        lookup[kind] = {str(pk): name for pk, name in rows}

    out = {}
    for node in nodes:
        config = node.config or {}
        for field in catalog.asset_fields_for(node.node_type):
            value = config.get(field.key)
            if not value:
                continue
            name = lookup.get(field.asset, {}).get(str(value))
            if name:
                out.setdefault(str(node.id), {})[field.key] = {
                    'kind': field.asset, 'name': name,
                }
    return out


def _jsonable(value):
    """Times and dates do not survive a JSON round trip on their own."""
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


# ──────────────────────────────────────────────────────────────── importing

def validate_definition(payload):
    """
    Check an uploaded payload before anything is created.

    Returns the cleaned dict. Raises DefinitionError with a sentence the
    uploader can act on — "invalid JSON" tells them nothing about which step
    is wrong.
    """
    if not isinstance(payload, dict):
        raise DefinitionError('The file does not contain a workflow.')

    if payload.get('format') != FORMAT:
        raise DefinitionError(
            'This file is not a workflow export from this platform.'
        )
    if int(payload.get('version') or 0) > VERSION:
        raise DefinitionError(
            'This export was made by a newer version of the platform.'
        )

    nodes = payload.get('nodes')
    if not isinstance(nodes, list) or not nodes:
        raise DefinitionError('The workflow has no steps.')
    if len(nodes) > MAX_NODES:
        raise DefinitionError(
            f'A workflow may have at most {MAX_NODES} steps; this one has {len(nodes)}.'
        )

    edges = payload.get('edges') or []
    if not isinstance(edges, list):
        raise DefinitionError('The connections between steps are not readable.')
    if len(edges) > MAX_EDGES:
        raise DefinitionError(f'A workflow may have at most {MAX_EDGES} connections.')

    unknown = sorted({
        node.get('node_type') for node in nodes
        if isinstance(node, dict) and not catalog.exists(node.get('node_type'))
    } - {None})
    if unknown:
        # Named rather than dropped: silently losing a step would produce a
        # workflow that looks complete and does something different.
        raise DefinitionError(
            'This workflow uses steps this version does not have: '
            + ', '.join(unknown)
        )

    if not any(
        catalog.spec_for(node.get('node_type')).category == catalog.TRIGGER
        for node in nodes if isinstance(node, dict)
    ):
        raise DefinitionError('The workflow has no trigger, so nothing would start it.')

    return payload


@transaction.atomic
def build_from_definition(organization, payload, user=None, name_override=''):
    """
    Create a workflow from portable data, re-pointing its references.

    Always a draft: an imported or generated workflow has had no review, and
    one that started mailing on arrival would be indefensible.

    Returns (workflow, report) where report lists what could not be placed.
    """
    resolver = AssetResolver(organization)
    settings_in = payload.get('workflow') or {}

    workflow = Workflow.objects.create(
        organization=organization,
        name=name_override or settings_in.get('name') or 'Imported workflow',
        description=settings_in.get('description') or '',
        status='draft',
        canvas_data=payload.get('canvas') or {},
        created_by=user,
        **_portable_settings(settings_in),
    )

    by_old_id = {}
    for raw in payload.get('nodes') or []:
        if not isinstance(raw, dict) or not catalog.exists(raw.get('node_type')):
            continue
        node_type = raw['node_type']
        spec = catalog.spec_for(node_type)
        label = (raw.get('label') or '')[:100]

        node = WorkflowNode.objects.create(
            workflow=workflow,
            node_type=node_type,
            label=label,
            position_x=_number(raw.get('position_x')),
            position_y=_number(raw.get('position_y')),
            config=_resolved_config(raw, spec, resolver, label or spec.label),
        )
        if raw.get('id'):
            by_old_id[str(raw['id'])] = node

    for raw in payload.get('edges') or []:
        if not isinstance(raw, dict):
            continue
        source = by_old_id.get(str(raw.get('source_node_id')))
        target = by_old_id.get(str(raw.get('target_node_id')))
        if not (source and target):
            continue
        WorkflowEdge.objects.create(
            workflow=workflow,
            source_node=source,
            target_node=target,
            edge_type=raw.get('edge_type') or 'default',
            source_handle=(raw.get('source_handle') or 'default')[:50],
            target_handle=(raw.get('target_handle') or 'default')[:50],
        )

    report = {
        'nodes_created': len(by_old_id),
        'edges_created': workflow.edges.count(),
        'unresolved': resolver.unresolved,
        # Every unplaced reference is a step that will fail when a contact
        # reaches it, so this is the list to show before activating.
        'needs_attention': sorted({item['node'] for item in resolver.unresolved}),
    }
    return workflow, report


def _portable_settings(settings_in):
    """The workflow-level settings an import is allowed to set."""
    allowed = {}
    for field in PORTABLE_FIELDS:
        if field in ('name', 'description') or field not in settings_in:
            continue
        allowed[field] = settings_in[field]

    # A value outside the model's choices would be written straight to the
    # column, so the one field that drives behaviour is checked.
    if allowed.get('reentry') not in dict(Workflow.REENTRY_CHOICES):
        allowed.pop('reentry', None)
    if not isinstance(allowed.get('send_weekdays', []), list):
        allowed.pop('send_weekdays', None)
    if not isinstance(allowed.get('goal_rules', {}), dict):
        allowed.pop('goal_rules', None)
    try:
        allowed['reentry_cooldown_days'] = max(
            0, int(allowed.get('reentry_cooldown_days', 0))
        )
    except (TypeError, ValueError):
        allowed.pop('reentry_cooldown_days', None)
    return allowed


def _resolved_config(raw, spec, resolver, where):
    """
    One node's config with its references re-pointed at this account.

    Keys the catalogue does not declare are kept: a node type may have gained
    settings since the export, and dropping what we do not recognise would
    quietly change what the step does.
    """
    config = dict(raw.get('config') or {})
    assets = raw.get('assets') or {}

    for field in spec.asset_fields:
        original = config.get(field.key)
        if not original:
            continue
        recorded = assets.get(field.key) or {}
        resolved = resolver.resolve(
            field.asset, original, recorded.get('name', ''), where=where,
        )
        if resolved:
            config[field.key] = resolved
        else:
            # Cleared rather than left dangling: an id from another account
            # must not survive into this one, even unusable.
            config[field.key] = ''
    return config


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
