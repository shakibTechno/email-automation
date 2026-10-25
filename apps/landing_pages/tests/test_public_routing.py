"""
Resolving a public landing page URL to exactly one tenant's page.

Page slugs are unique per organization, not globally, so the hostname or the
URL has to carry the tenant. Before this, `/p/<slug>/` looked the slug up
across every tenant: the first two customers to publish a "pricing" page broke
both of their pages with a 500, and until then the URL resolved across a tenant
boundary. These tests pin the collision, because it is the expected case rather
than a corner one.
"""
from django.test import TestCase

from apps.accounts.models import Organization
from apps.landing_pages.models import LandingPage


class PublicLandingPageRoutingTests(TestCase):
    def setUp(self):
        self.alpha = Organization.objects.create(name='Alpha', slug='alpha')
        self.beta = Organization.objects.create(name='Beta', slug='beta')

    def _page(self, org, slug, status='published', name=None):
        return LandingPage.objects.create(
            organization=org,
            name=name or slug.replace('-', ' ').title(),
            slug=slug,
            status=status,
            html_content=f'<h1>{org.slug}:{slug}</h1>',
        )

    # ------------------------------------------------------- org-scoped form
    def test_org_scoped_url_serves_that_organizations_page(self):
        self._page(self.alpha, 'pricing')
        self._page(self.beta, 'pricing')

        response = self.client.get('/p/alpha/pricing/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('alpha:pricing', response.content.decode())

    def test_org_scoped_url_does_not_leak_across_tenants(self):
        """Beta has no such page; Alpha's must not answer for it."""
        self._page(self.alpha, 'pricing')

        response = self.client.get('/p/beta/pricing/')

        self.assertEqual(response.status_code, 404)

    def test_public_url_is_org_scoped(self):
        page = self._page(self.alpha, 'pricing')

        self.assertTrue(page.public_url.endswith('/p/alpha/pricing'))

    def test_draft_pages_are_not_public(self):
        self._page(self.alpha, 'secret', status='draft')

        self.assertEqual(self.client.get('/p/alpha/secret/').status_code, 404)

    # ----------------------------------------------------------- legacy form
    def test_legacy_url_still_resolves_while_a_slug_is_unique(self):
        """Links published before the scoped route existed keep working."""
        self._page(self.alpha, 'solo')

        response = self.client.get('/p/solo/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('alpha:solo', response.content.decode())

    def test_legacy_url_refuses_to_guess_when_two_tenants_share_a_slug(self):
        """
        The failure this whole change exists for. Previously `.get()` raised
        MultipleObjectsReturned and both tenants' pages returned 500; serving
        either one would have been worse than serving neither.
        """
        self._page(self.alpha, 'pricing')
        self._page(self.beta, 'pricing')

        response = self.client.get('/p/pricing/')

        self.assertEqual(response.status_code, 404)
        body = response.content.decode()
        # Same response a missing page gets: a visitor must not be able to
        # discover that another tenant holds this slug.
        self.assertNotIn('alpha', body)
        self.assertNotIn('beta', body)

    def test_legacy_url_404s_for_an_unknown_slug(self):
        self.assertEqual(self.client.get('/p/nothing-here/').status_code, 404)

    # ------------------------------------------------------------- analytics
    def test_serving_a_page_records_one_view(self):
        page = self._page(self.alpha, 'pricing')
        self._page(self.beta, 'pricing')

        self.client.get('/p/alpha/pricing/')
        self.client.get('/p/pricing/')  # ambiguous: must not count

        self.assertEqual(page.page_views.count(), 1)
