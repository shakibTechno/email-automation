"""
Every routed viewset must scope its queryset to one tenant.

Isolation here is a per-viewset convention rather than something the framework
enforces. All of them are correct today; nothing stops the next one being
written without the filter. That failure is silent and total — DRF calls
`has_object_permission` only for detail routes, so an unscoped viewset passes
every permission check and returns every organization's rows from its list
endpoint, with no error anywhere.

This walks Django's URL resolver rather than grepping, so a viewset cannot
escape the check by living somewhere unexpected: if it is routed, it is tested.
"""
import inspect

from django.test import TestCase
from django.urls import get_resolver
from rest_framework.viewsets import ViewSetMixin

from apps.core.viewsets import OrganizationScopedQuerysetMixin

# Viewsets that legitimately do not filter by organization. Each needs a reason
# — this list is the only way past the check, so it should stay short and every
# addition should be deliberate.
ALLOWED_UNSCOPED = {
    # Serves public form rendering and submission at /f/<id>, unauthenticated
    # by design (permission_classes = [AllowAny]). Scoping by organization
    # would be meaningless: there is no user.
    'PublicFormViewSet',

    # Scoped by `user=self.request.user`, which is equivalent isolation — a
    # user belongs to exactly one organization — and is the more precise filter
    # here, since notifications are per-user rather than per-org.
    'NotificationViewSet',
}

# Evidence that a queryset is tenant-scoped, looked for in the source of
# get_queryset(). Deliberately permissive about *how* it is written, since the
# viewsets predate the mixin and each spells it slightly differently.
_SCOPING_MARKERS = (
    'request.user.organization',
    'user=self.request.user',
    'user=request.user',
)


def _routed_viewsets():
    """Every viewset class reachable through the URL conf, de-duplicated."""
    found = {}

    def walk(patterns, prefix=''):
        for pattern in patterns:
            if hasattr(pattern, 'url_patterns'):
                walk(pattern.url_patterns, prefix + str(pattern.pattern))
                continue
            cls = getattr(getattr(pattern, 'callback', None), 'cls', None)
            if cls is not None and issubclass(cls, ViewSetMixin):
                found[cls.__name__] = cls

    walk(get_resolver().url_patterns)
    return found


class TenantIsolationGuardTestCase(TestCase):
    def test_every_routed_viewset_is_tenant_scoped(self):
        viewsets = _routed_viewsets()

        self.assertGreater(
            len(viewsets), 20,
            'found almost no viewsets — the resolver walk is broken, and a '
            'guard that inspects nothing silently passes forever',
        )

        unscoped = []
        for name, cls in sorted(viewsets.items()):
            if name in ALLOWED_UNSCOPED:
                continue
            if issubclass(cls, OrganizationScopedQuerysetMixin):
                continue

            get_queryset = getattr(cls, 'get_queryset', None)
            if get_queryset is None:
                unscoped.append(f'{name}: no get_queryset() at all')
                continue

            try:
                source = inspect.getsource(get_queryset)
            except (OSError, TypeError):
                unscoped.append(f'{name}: get_queryset() source unavailable')
                continue

            if not any(marker in source for marker in _SCOPING_MARKERS):
                unscoped.append(f'{name}: get_queryset() does not filter by tenant')

        self.assertEqual(
            unscoped, [],
            'These viewsets would expose every tenant\'s rows on their list '
            'endpoint:\n  ' + '\n  '.join(unscoped) +
            '\n\nInherit OrganizationScopedQuerysetMixin from apps.core.viewsets, '
            'or add the class to ALLOWED_UNSCOPED with a reason if it is '
            'genuinely public.'
        )

    def test_the_guard_actually_catches_an_unscoped_viewset(self):
        """
        A guard that cannot fail is worse than none, because it reads as
        protection while providing none. This proves it rejects the exact shape
        it exists to catch.
        """
        from rest_framework import viewsets
        from apps.contacts.models import Contact

        class LeakyViewSet(viewsets.ModelViewSet):
            queryset = Contact.objects.all()  # no tenant filter

        source = inspect.getsource(LeakyViewSet.get_queryset)
        self.assertFalse(
            any(marker in source for marker in _SCOPING_MARKERS),
            'the inherited get_queryset() should show no scoping markers',
        )
        self.assertFalse(issubclass(LeakyViewSet, OrganizationScopedQuerysetMixin))


class OrganizationScopedMixinTestCase(TestCase):
    """The mixin itself, which new viewsets are meant to use."""

    def setUp(self):
        from apps.accounts.models import Organization, User
        from apps.contacts.models import Contact

        self.org_a = Organization.objects.create(name='A Co', slug='a-co')
        self.org_b = Organization.objects.create(name='B Co', slug='b-co')
        self.user_a = User.objects.create_user(
            email='a@test.co', password='x', organization=self.org_a, role='owner',
        )
        Contact.objects.create(organization=self.org_a, email='mine@test.co')
        Contact.objects.create(organization=self.org_b, email='theirs@test.co')

    def _view(self, user):
        from rest_framework import viewsets
        from apps.contacts.models import Contact

        class ScopedViewSet(OrganizationScopedQuerysetMixin, viewsets.ModelViewSet):
            queryset = Contact.objects.all()

        view = ScopedViewSet()
        view.request = type('R', (), {'user': user})()
        return view

    def test_only_the_users_own_organization_is_visible(self):
        emails = list(self._view(self.user_a).get_queryset().values_list('email', flat=True))
        self.assertEqual(emails, ['mine@test.co'])

    def test_a_user_without_an_organization_sees_nothing(self):
        """Fails closed rather than falling through to an unfiltered queryset."""
        from apps.accounts.models import User

        orphan = User.objects.create_user(
            email='orphan@test.co', password='x', organization=None,
        )
        self.assertEqual(self._view(orphan).get_queryset().count(), 0)
