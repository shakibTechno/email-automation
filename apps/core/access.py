"""
The single declaration of what a role may do.

Every permission is the string ``<resource>.<verb>``: one resource per feature
area, one verb per kind of action. The four built-in roles are presets over
those codes and a custom role is a stored list of them, so there is exactly one
vocabulary and one answer to "may this user do this".

Nothing else may decide access. A role check written inline at the call site is
how ``isProfessionalOrAbove`` came to exclude Business customers; the same
drift in access control is a privilege hole rather than a missing feature.
"""
from __future__ import annotations

VIEW = 'view'
CREATE = 'create'
EDIT = 'edit'
DELETE = 'delete'
MANAGE = 'manage'

# Content a marketer works on day to day: full CRUD, plus `manage` for the
# actions that reach the outside world (sending, publishing, activating).
CRUD = (VIEW, CREATE, EDIT, DELETE, MANAGE)
# Organization configuration: there is nothing to "create" or "delete", you
# either see the settings or you change them.
CONFIG = (VIEW, MANAGE)
# Read-only surfaces.
READ = (VIEW,)

RESOURCES = {
    'contacts': {
        'label': 'Contacts',
        'group': 'Audience',
        'verbs': CRUD,
        'manage_label': 'Import and bulk actions',
    },
    'segments': {
        'label': 'Segments',
        'group': 'Audience',
        'verbs': CRUD,
        'manage_label': 'Refresh and membership',
    },
    'templates': {
        'label': 'Email templates',
        'group': 'Content',
        'verbs': CRUD,
        'manage_label': 'Shared template actions',
    },
    'forms': {
        'label': 'Forms',
        'group': 'Content',
        'verbs': CRUD,
        'manage_label': 'Publish and unpublish',
    },
    'popups': {
        'label': 'Pop-ups',
        'group': 'Content',
        'verbs': CRUD,
        'manage_label': 'Activate and deactivate',
    },
    'landing_pages': {
        'label': 'Landing pages',
        'group': 'Content',
        'verbs': CRUD,
        'manage_label': 'Publish and domains',
    },
    'campaigns': {
        'label': 'Campaigns',
        'group': 'Messaging',
        'verbs': CRUD,
        'manage_label': 'Send, pause, resume, cancel',
    },
    'sequences': {
        'label': 'Sequences',
        'group': 'Messaging',
        'verbs': CRUD,
        'manage_label': 'Activate, pause, enroll',
    },
    'workflows': {
        'label': 'Workflows',
        'group': 'Automation',
        'verbs': CRUD,
        'manage_label': 'Activate and deactivate',
    },
    'lead_scoring': {
        'label': 'Lead scoring',
        'group': 'Automation',
        'verbs': CRUD,
        'manage_label': 'Recalculate scores',
    },
    'crm': {
        'label': 'CRM and pipelines',
        'group': 'Sales',
        'verbs': CRUD,
        'manage_label': 'Pipeline and stage setup',
    },
    'analytics': {
        'label': 'Analytics and dashboard',
        'group': 'Insights',
        'verbs': READ,
    },
    'team': {
        'label': 'Team',
        'group': 'Settings',
        'verbs': CONFIG,
        'manage_label': 'Invite, change roles, remove, manage roles',
    },
    'billing': {
        'label': 'Billing',
        'group': 'Settings',
        'verbs': CONFIG,
        'manage_label': 'Change plan and payment methods',
    },
    'email_config': {
        'label': 'Email settings',
        'group': 'Settings',
        'verbs': CONFIG,
        'manage_label': 'Provider, domains, sending limits',
    },
    'integrations': {
        'label': 'Integrations',
        'group': 'Settings',
        'verbs': CONFIG,
        'manage_label': 'Connect, disconnect, sync',
    },
    'ai_assistant': {
        'label': 'AI assistant',
        'group': 'Settings',
        'verbs': CONFIG,
        'manage_label': 'Provider and API key',
    },
}

VERB_LABELS = {
    VIEW: 'View',
    CREATE: 'Create',
    EDIT: 'Edit',
    DELETE: 'Delete',
    MANAGE: 'Manage',
}

ALL_PERMISSIONS = frozenset(
    f'{resource}.{verb}'
    for resource, spec in RESOURCES.items()
    for verb in spec['verbs']
)

# A view's resource is its app, which keeps the mapping zero-maintenance: a new
# endpoint in apps/campaigns/ is a campaigns endpoint. Only apps whose name is
# not the resource name need an entry here.
MODULE_RESOURCE = {
    'accounts': 'team',   # the team-management views live with the auth views
    'core': 'analytics',  # the dashboard
}

# ViewSet actions whose HTTP method implies the wrong verb. Everything else is
# derived from the method (GET -> view, POST -> create, PUT/PATCH -> edit,
# DELETE -> delete), so a new custom action needs no entry unless it is
# privileged.
ACTION_VERBS = {
    'bulk_delete': DELETE,
    'send': MANAGE,
    # `send_test` is deliberately absent: a test send goes to one address the
    # sender chose, and whoever may write a campaign has always been able to
    # proof it. It resolves to `create` like any other POST.
    'pause': MANAGE,
    'resume': MANAGE,
    'cancel': MANAGE,
    'publish': MANAGE,
    'unpublish': MANAGE,
    'activate': MANAGE,
    'deactivate': MANAGE,
    'toggle_status': MANAGE,
}

METHOD_VERBS = {
    'GET': VIEW,
    'HEAD': VIEW,
    'OPTIONS': VIEW,
    'POST': CREATE,
    'PUT': EDIT,
    'PATCH': EDIT,
    'DELETE': DELETE,
}

BUILTIN_ROLES = {
    'owner': 'Owner',
    'admin': 'Admin',
    'member': 'Member',
    'viewer': 'Viewer',
}
# 'owner' is reached by transferring ownership, never by assignment.
ASSIGNABLE_BUILTIN_ROLES = ('admin', 'member', 'viewer')

# Roles are not a plan feature. Deciding who on your team may delete contacts
# or send a campaign is how an account stays safe, so it is not something to
# withhold from the plans that can least afford a mistake.


def _preset(verbs):
    """Permissions for every resource, limited to the `verbs` it defines."""
    return frozenset(
        f'{resource}.{verb}'
        for resource, spec in RESOURCES.items()
        for verb in spec['verbs']
        if verb in verbs
    )


PRESETS = {
    'owner': ALL_PERMISSIONS,
    'admin': ALL_PERMISSIONS,
    # A member works on content but does not delete it, does not send or
    # publish, and does not change organization settings.
    'member': _preset({VIEW, CREATE, EDIT}),
    'viewer': _preset({VIEW}),
}


def collapse_verb(resource, verb):
    """
    The nearest verb `resource` actually defines.

    A CONFIG resource has no create/edit/delete, so any write against it is a
    `manage`. Without this, PUT /email-config/ would ask for `email_config.edit`
    - a code no role can hold - and the endpoint would be dead for everyone.
    """
    verbs = RESOURCES[resource]['verbs']
    if verb in verbs:
        return verb
    if verb == VIEW:
        return None
    return MANAGE if MANAGE in verbs else None


def required_permission(view, request, verb=None):
    """
    The permission code this request needs, or None when it cannot be resolved.

    None means deny: an endpoint outside the registry must fail closed, or
    adding a resource without declaring it would quietly grant it to everyone.
    """
    resource = getattr(view, 'permission_resource', None)
    if resource is None:
        parts = type(view).__module__.split('.')
        app = parts[1] if len(parts) > 1 and parts[0] == 'apps' else None
        resource = MODULE_RESOURCE.get(app, app)
    if resource not in RESOURCES:
        return None

    verb = getattr(view, 'permission_verb', None) or verb
    if verb is None:
        action = getattr(view, 'action', None)
        verb = ACTION_VERBS.get(action) or METHOD_VERBS.get(request.method)
        if verb is None:
            return None

    verb = collapse_verb(resource, verb)
    return None if verb is None else f'{resource}.{verb}'


def permissions_for(user):
    """
    Every permission code `user` holds, as a frozenset.

    Cached on the user instance: a request builds one user object and the
    permission classes ask several times per request.
    """
    cached = getattr(user, '_access_permissions', None)
    if cached is not None:
        return cached

    permissions = frozenset()
    organization = getattr(user, 'organization', None)
    if organization is not None:
        role = getattr(user, 'role', None)
        preset = PRESETS.get(role)
        if preset is not None:
            permissions = preset
        else:
            from apps.accounts.models import Role

            custom = Role.objects.filter(
                organization=organization, slug=role
            ).first()
            # A role deleted out from under its members grants nothing, rather
            # than falling back to a preset.
            permissions = frozenset(custom.permissions) if custom else frozenset()

    user._access_permissions = permissions
    return permissions


def has_permission(user, code):
    """True when `user` holds `code`. The owner always does."""
    if getattr(user, 'organization', None) is None:
        return False
    if getattr(user, 'role', None) == 'owner':
        # Insurance against locking an account's owner out of their own
        # organization, whatever state the role rows are in.
        return True
    return code in permissions_for(user)


def catalog():
    """The registry in the shape the settings UI renders it."""
    return {
        'resources': [
            {
                'key': key,
                'label': spec['label'],
                'group': spec['group'],
                'verbs': [
                    {
                        'key': verb,
                        'label': (
                            spec.get('manage_label', VERB_LABELS[verb])
                            if verb == MANAGE else VERB_LABELS[verb]
                        ),
                        'code': f'{key}.{verb}',
                    }
                    for verb in spec['verbs']
                ],
            }
            for key, spec in RESOURCES.items()
        ],
        'presets': [
            {
                'slug': slug,
                'name': name,
                'permissions': sorted(PRESETS[slug]),
                'assignable': slug in ASSIGNABLE_BUILTIN_ROLES,
            }
            for slug, name in BUILTIN_ROLES.items()
        ],
    }
