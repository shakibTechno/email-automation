"""
The permission registry has to stay the thing that decides access.

Three ways it could rot, each silent:

- a new app's endpoints resolve to no resource, so the permission class denies
  everyone (fail closed, but a dead feature nobody traces back to here);
- a resource is declared and the presets quietly hand it to every role;
- the matrix in the registry drifts from the matrix that was agreed, and
  nothing says so because the code is self-consistent either way.

So the matrix is written out here by hand and compared, and the URL conf is
walked rather than grepped: if a view is routed and carries the permission
class, it is checked.
"""
from django.test import TestCase
from django.urls import get_resolver
from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import ViewSetMixin

from apps.core import access
from apps.core.permissions import HasResourcePermission

# The agreed matrix, one row per resource, one column per built-in role:
#   V view, C create, E edit, D delete, M manage
# A resource that does not define a verb cannot grant it, so 'VCEDM' on a
# view-only resource would be a declaration error, not extra access.
MATRIX = {
    #                 owner    admin    member  viewer
    'contacts':      ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'segments':      ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'templates':     ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'forms':         ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'popups':        ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'landing_pages': ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'campaigns':     ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'sequences':     ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'workflows':     ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'lead_scoring':  ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'crm':           ('VCEDM', 'VCEDM', 'VCE',  'V'),
    'analytics':     ('V',     'V',     'V',    'V'),
    'team':          ('VM',    'VM',    'V',    'V'),
    'billing':       ('VM',    'VM',    'V',    'V'),
    'email_config':  ('VM',    'VM',    'V',    'V'),
    'integrations':  ('VM',    'VM',    'V',    'V'),
    'ai_assistant':  ('VM',    'VM',    'V',    'V'),
}

LETTERS = {
    'V': access.VIEW,
    'C': access.CREATE,
    'E': access.EDIT,
    'D': access.DELETE,
    'M': access.MANAGE,
}

ROLE_COLUMNS = ('owner', 'admin', 'member', 'viewer')

# The actions the old role check named as off-limits to a member. They are the
# privileged ones — sending mail, publishing a page, deleting in bulk — and
# each must still resolve to a verb a member does not hold.
PREVIOUSLY_RESTRICTED = {
    'bulk_delete', 'send', 'pause', 'resume', 'cancel',
    'publish', 'unpublish', 'activate', 'deactivate', 'toggle_status',
}


def _gated_view_classes():
    """Every routed view class whose access is decided by the registry."""
    found = {}

    def walk(patterns):
        for pattern in patterns:
            if hasattr(pattern, 'url_patterns'):
                walk(pattern.url_patterns)
                continue
            cls = getattr(getattr(pattern, 'callback', None), 'cls', None)
            if cls is None:
                continue
            classes = getattr(cls, 'permission_classes', []) or []
            if any(
                isinstance(permission, type)
                and issubclass(permission, HasResourcePermission)
                for permission in classes
            ):
                found[f'{cls.__module__}.{cls.__name__}'] = cls

    walk(get_resolver().url_patterns)
    return found


class PermissionMatrixTestCase(TestCase):
    def test_the_presets_are_the_agreed_matrix(self):
        self.assertEqual(
            sorted(MATRIX), sorted(access.RESOURCES),
            'A resource was added or removed without deciding what each '
            'built-in role may do with it.',
        )

        for index, role in enumerate(ROLE_COLUMNS):
            expected = set()
            for resource, columns in MATRIX.items():
                for letter in columns[index]:
                    verb = LETTERS[letter]
                    self.assertIn(
                        verb, access.RESOURCES[resource]['verbs'],
                        f'{resource} does not define "{verb}", so no role can '
                        f'be granted {resource}.{verb}',
                    )
                    expected.add(f'{resource}.{verb}')

            self.assertEqual(
                set(access.PRESETS[role]), expected,
                f'The {role} preset no longer matches the matrix. Granted but '
                f'not in the matrix: {sorted(set(access.PRESETS[role]) - expected)}. '
                f'In the matrix but not granted: {sorted(expected - set(access.PRESETS[role]))}.',
            )

    def test_owner_and_admin_hold_everything(self):
        self.assertEqual(access.PRESETS['owner'], access.ALL_PERMISSIONS)
        self.assertEqual(access.PRESETS['admin'], access.ALL_PERMISSIONS)

    def test_a_viewer_can_only_read(self):
        self.assertTrue(
            all(code.endswith('.view') for code in access.PRESETS['viewer'])
        )

    def test_a_member_cannot_delete_send_or_configure(self):
        member = access.PRESETS['member']
        self.assertNotIn('contacts.delete', member)
        self.assertNotIn('campaigns.manage', member)
        self.assertNotIn('team.manage', member)
        self.assertNotIn('billing.manage', member)
        # ...but still does the work
        self.assertIn('campaigns.create', member)
        self.assertIn('contacts.edit', member)

    def test_the_privileged_actions_are_still_privileged(self):
        member = access.PRESETS['member']
        for action in PREVIOUSLY_RESTRICTED:
            verb = access.ACTION_VERBS.get(action)
            self.assertIsNotNone(
                verb, f'action "{action}" no longer maps to a verb, so it '
                'resolves to its HTTP method and a member can do it',
            )
            self.assertNotIn(
                f'campaigns.{verb}', member,
                f'action "{action}" maps to "{verb}", which a member holds',
            )


class ResourceResolutionTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_every_gated_view_resolves_to_a_declared_resource(self):
        views = _gated_view_classes()
        self.assertGreater(
            len(views), 30,
            'found almost no gated views - the resolver walk is broken, and a '
            'guard that inspects nothing passes forever',
        )

        unresolved = []
        for name, cls in sorted(views.items()):
            code = access.required_permission(cls(), self.factory.get('/'))
            if code is None:
                unresolved.append(name)

        self.assertEqual(
            unresolved, [],
            'These endpoints deny every user, because their app is not a '
            'resource in apps/core/access.py:\n  ' + '\n  '.join(unresolved) +
            '\n\nAdd the resource to RESOURCES, map the app in '
            'MODULE_RESOURCE, or set permission_resource on the view.'
        )

    def test_every_method_a_gated_view_answers_resolves(self):
        """
        A view can resolve for GET and still be dead for POST - that is what
        happens when a write lands on a resource with no verb for it.
        """
        viewset_actions = {
            'list': 'get', 'retrieve': 'get', 'create': 'post',
            'update': 'put', 'partial_update': 'patch', 'destroy': 'delete',
        }

        dead = []
        for name, cls in sorted(_gated_view_classes().items()):
            if issubclass(cls, ViewSetMixin):
                for action, method in viewset_actions.items():
                    if not hasattr(cls, action):
                        continue
                    view = cls()
                    view.action = action
                    request = getattr(self.factory, method)('/')
                    if access.required_permission(view, request) is None:
                        dead.append(f'{name} {action}')
                continue

            for method in ('get', 'post', 'put', 'patch', 'delete'):
                if not hasattr(cls, method):
                    continue
                request = getattr(self.factory, method)('/')
                if access.required_permission(cls(), request) is None:
                    dead.append(f'{name} {method.upper()}')

        self.assertEqual(
            dead, [],
            'These endpoints exist but no permission can reach them:\n  '
            + '\n  '.join(dead)
        )

    def test_an_undeclared_app_fails_closed(self):
        class StrayView:
            pass

        StrayView.__module__ = 'apps.not_a_real_app.views'
        self.assertIsNone(
            access.required_permission(StrayView(), self.factory.get('/'))
        )

    def test_a_write_to_a_read_only_resource_resolves_to_nothing(self):
        self.assertIsNone(access.collapse_verb('analytics', access.EDIT))

    def test_a_write_to_a_config_resource_is_a_manage(self):
        for verb in (access.CREATE, access.EDIT, access.DELETE):
            self.assertEqual(
                access.collapse_verb('billing', verb), access.MANAGE
            )
