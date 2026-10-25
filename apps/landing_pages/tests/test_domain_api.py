"""
Connecting, verifying and choosing between landing-page domains.
"""
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.landing_pages.domain_service import DomainError, LandingDomainService
from apps.landing_pages.models import LandingDomain, LandingPage

PLATFORM = ['localhost', '127.0.0.1', 'testserver', 'backend', 'app.example.com']


class FakeResponse:
    def __init__(self, status_code=200, text=''):
        self.status_code = status_code
        self.text = text


@override_settings(PLATFORM_HOSTS=PLATFORM, BACKEND_URL='https://app.example.com')
class DomainApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.org = Organization.objects.create(name='Alpha', slug='alpha', plan='starter')
        self.user = User.objects.create_user(
            email='owner@alpha.test', password='x', organization=self.org, role='owner',
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    # ------------------------------------------------------------- plan gate
    def test_free_plan_is_refused(self):
        self.org.plan = 'free'
        self.org.save()

        response = self.api.post('/api/v1/landing-domains/', {'domain': 'go.alpha.test'})

        self.assertEqual(response.status_code, 403)

    def test_starter_plan_is_allowed(self):
        response = self.api.post(
            '/api/v1/landing-domains/', {'domain': 'go.alpha-example.com'},
        )

        self.assertEqual(response.status_code, 201)

    def test_a_tier_above_the_minimum_is_allowed(self):
        """The bug the lead-scoring gate already had: a tuple of tiers excluded Business."""
        self.org.plan = 'business'
        self.org.save()

        response = self.api.post(
            '/api/v1/landing-domains/', {'domain': 'go.alpha-example.com'},
        )

        self.assertEqual(response.status_code, 201)

    # --------------------------------------------------------- what may be used
    def test_the_platform_host_cannot_be_claimed(self):
        response = self.api.post('/api/v1/landing-domains/', {'domain': 'app.example.com'})

        self.assertEqual(response.status_code, 400)

    def test_a_subdomain_of_the_platform_cannot_be_claimed(self):
        response = self.api.post('/api/v1/landing-domains/', {'domain': 'evil.app.example.com'})

        self.assertEqual(response.status_code, 400)

    def test_a_url_is_accepted_and_reduced_to_its_hostname(self):
        response = self.api.post(
            '/api/v1/landing-domains/', {'domain': 'HTTPS://Go.Alpha-Example.com/pricing'},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['domain'], 'go.alpha-example.com')

    def test_nonsense_is_refused(self):
        for value in ['', 'not a domain', 'localhost', 'example', 'go_underscore.test']:
            with self.subTest(value=value):
                response = self.api.post('/api/v1/landing-domains/', {'domain': value})
                self.assertEqual(response.status_code, 400)

    def test_another_organization_cannot_take_a_connected_domain(self):
        LandingDomain.objects.create(
            organization=Organization.objects.create(name='Beta', slug='beta'),
            domain='go.alpha-example.com',
        )

        response = self.api.post(
            '/api/v1/landing-domains/', {'domain': 'go.alpha-example.com'},
        )

        self.assertEqual(response.status_code, 400)
        # Must not confirm that another tenant holds it.
        self.assertNotIn('beta', str(response.data).lower())

    # ------------------------------------------------------------- isolation
    def test_the_list_shows_only_this_organizations_domains(self):
        LandingDomain.objects.create(organization=self.org, domain='mine.example.com')
        LandingDomain.objects.create(
            organization=Organization.objects.create(name='Beta', slug='beta'),
            domain='theirs.example.com',
        )

        response = self.api.get('/api/v1/landing-domains/')

        domains = [row['domain'] for row in response.data['results']]
        self.assertEqual(domains, ['mine.example.com'])

    # --------------------------------------------------------------- primary
    def test_the_first_domain_becomes_primary(self):
        first = LandingDomainService.connect(self.org, 'one.example.com')

        self.assertTrue(first.is_primary)

    def test_only_one_domain_is_primary_at_a_time(self):
        first = LandingDomainService.connect(self.org, 'one.example.com')
        second = LandingDomainService.connect(self.org, 'two.example.com')

        LandingDomainService.set_primary(second)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_removing_the_primary_promotes_another(self):
        first = LandingDomainService.connect(self.org, 'one.example.com')
        LandingDomainService.connect(self.org, 'two.example.com')

        LandingDomainService.disconnect(first)

        self.assertTrue(LandingDomain.objects.get(domain='two.example.com').is_primary)

    # ---------------------------------------------------------- verification
    def test_verification_succeeds_when_the_token_comes_back(self):
        domain = LandingDomainService.connect(self.org, 'go.alpha-example.com')

        with patch('apps.landing_pages.domain_service.requests.get') as get:
            get.return_value = FakeResponse(200, domain.verification_token)
            result = LandingDomainService.verify(domain)

        self.assertTrue(result.is_verified)
        self.assertEqual(result.last_check_error, '')
        self.assertIsNotNone(result.verified_at)

    def test_another_service_answering_does_not_verify(self):
        """
        Someone else's working HTTPS on that hostname must not count. This is
        why the check compares a token instead of trusting a 200.
        """
        domain = LandingDomainService.connect(self.org, 'go.alpha-example.com')

        with patch('apps.landing_pages.domain_service.requests.get') as get:
            get.return_value = FakeResponse(200, 'some other service')
            result = LandingDomainService.verify(domain)

        self.assertFalse(result.is_verified)
        self.assertIn('another service', result.last_check_error)

    def test_an_unreachable_domain_reports_dns_rather_than_failing(self):
        domain = LandingDomainService.connect(self.org, 'go.alpha-example.com')

        with patch('apps.landing_pages.domain_service.requests.get') as get:
            get.side_effect = requests.exceptions.ConnectionError()
            result = LandingDomainService.verify(domain)

        self.assertFalse(result.is_verified)
        self.assertIn('CNAME', result.last_check_error)

    def test_a_verified_domain_keeps_its_verified_at_through_a_blip(self):
        domain = LandingDomainService.connect(self.org, 'go.alpha-example.com')
        with patch('apps.landing_pages.domain_service.requests.get') as get:
            get.return_value = FakeResponse(200, domain.verification_token)
            domain = LandingDomainService.verify(domain)
        first_verified_at = domain.verified_at

        with patch('apps.landing_pages.domain_service.requests.get') as get:
            get.side_effect = requests.exceptions.Timeout()
            domain = LandingDomainService.verify(domain)

        self.assertEqual(domain.verified_at, first_verified_at)

    def test_verify_endpoint_returns_200_even_when_the_domain_is_not_ready(self):
        """A domain that is not pointed here yet is an answer, not an error."""
        domain = LandingDomainService.connect(self.org, 'go.alpha-example.com')

        with patch('apps.landing_pages.domain_service.requests.get') as get:
            get.side_effect = requests.exceptions.ConnectionError()
            response = self.api.post(f'/api/v1/landing-domains/{domain.id}/verify/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'failed')
        self.assertTrue(response.data['last_check_error'])

    def test_a_tenant_cannot_verify_another_tenants_domain(self):
        theirs = LandingDomain.objects.create(
            organization=Organization.objects.create(name='Beta', slug='beta'),
            domain='theirs.example.com',
        )

        response = self.api.post(f'/api/v1/landing-domains/{theirs.id}/verify/')

        self.assertEqual(response.status_code, 404)


@override_settings(PLATFORM_HOSTS=PLATFORM, BACKEND_URL='https://app.example.com')
class PublicUrlTests(TestCase):
    """`public_url` is the one seam every surface reads, so it is pinned hard."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.org = Organization.objects.create(name='Alpha', slug='alpha', plan='starter')
        self.page = LandingPage.objects.create(
            organization=self.org, name='Black Friday', slug='black-friday',
            status='published',
        )

    def test_platform_url_while_no_domain_is_connected(self):
        self.assertEqual(
            self.page.public_url, 'https://app.example.com/p/alpha/black-friday',
        )

    def test_still_the_platform_url_while_the_domain_is_unverified(self):
        """
        An unverified domain has no certificate and no working DNS. Showing it
        would hand the customer a link that does not load.
        """
        LandingDomain.objects.create(organization=self.org, domain='go.alpha-example.com')

        self.assertIn('/p/alpha/black-friday', self.page.public_url)

    def test_moves_to_the_domain_once_verified(self):
        LandingDomain.objects.create(
            organization=self.org, domain='go.alpha-example.com',
            status=LandingDomain.STATUS_VERIFIED,
        )

        self.assertEqual(
            self.page.public_url, 'https://go.alpha-example.com/black-friday',
        )

    def test_the_home_page_sits_at_the_domain_root(self):
        LandingDomain.objects.create(
            organization=self.org, domain='go.alpha-example.com',
            status=LandingDomain.STATUS_VERIFIED,
        )
        self.page.is_domain_home = True

        self.assertEqual(self.page.public_url, 'https://go.alpha-example.com')

    def test_platform_url_remains_available_as_a_fallback(self):
        LandingDomain.objects.create(
            organization=self.org, domain='go.alpha-example.com',
            status=LandingDomain.STATUS_VERIFIED,
        )

        self.assertIn('/p/alpha/black-friday', self.page.platform_url)
