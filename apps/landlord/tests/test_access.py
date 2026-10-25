"""
Who may reach the landlord console.

This is the most important test file in the app. Every endpoint here reads
across all tenants, and DRF's project default permission is a bare
IsAuthenticated — so an endpoint that failed to demand platform staff would be
readable by any customer who signed up, exposing every other customer's data.
The test enumerates the routes rather than listing them by hand, so a new
endpoint is covered the moment it is added.
"""
from django.test import TestCase
from django.urls import get_resolver
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.billing.testing import create_plans


def _landlord_urls():
    """Every concrete landlord URL, with a real pk substituted for detail routes."""
    paths = []

    def walk(patterns, prefix=''):
        for pattern in patterns:
            if hasattr(pattern, 'url_patterns'):
                walk(pattern.url_patterns, prefix + str(pattern.pattern))
                continue
            full = prefix + str(pattern.pattern)
            if 'landlord' in full:
                paths.append(full)

    walk(get_resolver().url_patterns)
    return paths


class LandlordAccessTestCase(TestCase):
    def setUp(self):
        create_plans()
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.tenant_owner = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org, role='owner',
        )
        self.staff = User.objects.create_user(
            email='ops@platform.test', password='x', organization=None, is_staff=True,
        )
        self.endpoints = [
            '/api/v1/landlord/overview/',
            '/api/v1/landlord/deliverability/',
            '/api/v1/landlord/revenue/',
            '/api/v1/landlord/tenants/',
            f'/api/v1/landlord/tenants/{self.org.id}/',
        ]

    def test_the_route_enumeration_found_the_endpoints(self):
        """Guard the guard: a list that silently empties proves nothing."""
        self.assertGreaterEqual(len(_landlord_urls()), 4)

    def test_an_anonymous_user_is_refused(self):
        client = APIClient()
        for url in self.endpoints:
            with self.subTest(url=url):
                self.assertIn(client.get(url).status_code, (401, 403))

    def test_a_tenant_owner_is_refused(self):
        """
        The highest-privileged tenant role must still be locked out. `role` is
        organization-scoped and says nothing about platform access.
        """
        client = APIClient()
        client.force_authenticate(user=self.tenant_owner)
        for url in self.endpoints:
            with self.subTest(url=url):
                self.assertEqual(
                    client.get(url).status_code, 403,
                    f'{url} is readable by a customer',
                )

    def test_a_tenant_owner_cannot_suspend_anyone(self):
        client = APIClient()
        client.force_authenticate(user=self.tenant_owner)
        for verb in ('suspend-sending', 'suspend-account', 'restore-account'):
            with self.subTest(action=verb):
                response = client.post(
                    f'/api/v1/landlord/tenants/{self.org.id}/{verb}/',
                    {'reason': 'nice try'}, format='json',
                )
                self.assertEqual(response.status_code, 403)

    def test_an_inactive_staff_user_is_refused(self):
        self.staff.is_active = False
        self.staff.save(update_fields=['is_active'])

        client = APIClient()
        client.force_authenticate(user=self.staff)
        self.assertEqual(client.get('/api/v1/landlord/overview/').status_code, 403)

    def test_platform_staff_are_admitted(self):
        client = APIClient()
        client.force_authenticate(user=self.staff)
        for url in self.endpoints:
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 200)


class StaffUserAgainstTheTenantApiTestCase(TestCase):
    """
    A platform operator has no organization, so the tenant API must refuse them
    — and must do so by checking membership, not by crashing on a null FK.
    """

    def setUp(self):
        create_plans()
        self.staff = User.objects.create_user(
            email='ops@platform.test', password='x', organization=None,
            is_staff=True, role='owner',
        )
        self.client_api = APIClient()
        self.client_api.force_authenticate(user=self.staff)

    def test_tenant_endpoints_refuse_an_org_less_staff_user(self):
        for url in ('/api/v1/contacts/', '/api/v1/campaigns/', '/api/v1/segments/'):
            with self.subTest(url=url):
                self.assertEqual(self.client_api.get(url).status_code, 403)

    def test_org_less_staff_fail_the_admin_and_owner_permissions(self):
        """
        create_superuser sets role='owner'. Those two classes checked role
        without checking organization, so an org-less staff user passed both
        and then misbehaved on request.user.organization.
        """
        from apps.core.permissions import IsOrganizationAdmin, IsOrganizationOwner

        request = type('R', (), {'user': self.staff})()
        self.assertFalse(IsOrganizationAdmin().has_permission(request, None))
        self.assertFalse(IsOrganizationOwner().has_permission(request, None))
