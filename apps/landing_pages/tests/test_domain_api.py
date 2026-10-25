"""
Connecting, verifying and choosing between landing-page domains.
"""
import socket
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.landing_pages.domain_service import DomainError, LandingDomainService
from apps.landing_pages.domains import doubled_name_candidate, split_zone
from apps.email_config.models import SendingDomain
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

    def test_a_hostname_that_does_not_resolve_says_so(self):
        """
        Distinct from "resolves but refuses". Reporting the wrong one sent
        someone to wait three hours on propagation of a record their DNS host
        had refused.
        """
        domain = LandingDomainService.connect(self.org, 'go.alpha-example.com')

        exc = requests.exceptions.ConnectionError('boom')
        exc.__cause__ = socket.gaierror(-2, 'Name or service not known')
        with patch('apps.landing_pages.domain_service.requests.get') as get,                 patch('apps.landing_pages.domain_service.resolves', return_value=False):
            get.side_effect = exc
            result = LandingDomainService.verify(domain)

        self.assertFalse(result.is_verified)
        self.assertIn('does not resolve', result.last_check_error)

    def test_a_refused_connection_says_it_points_elsewhere(self):
        domain = LandingDomainService.connect(self.org, 'go.alpha-example.com')

        with patch('apps.landing_pages.domain_service.requests.get') as get:
            get.side_effect = requests.exceptions.ConnectionError(
                '[Errno 111] Connection refused'
            )
            result = LandingDomainService.verify(domain)

        self.assertFalse(result.is_verified)
        self.assertIn('refused the connection', result.last_check_error)

    def test_a_sending_domain_that_does_not_resolve_is_told_why(self):
        """The exact case that failed: the CNAME could never have been added."""
        SendingDomain.objects.create(
            organization=self.org, domain='news.alpha-example.com',
            status=SendingDomain.STATUS_VERIFIED,
        )
        domain = LandingDomainService.connect(self.org, 'news.alpha-example.com')

        exc = requests.exceptions.ConnectionError('boom')
        exc.__cause__ = socket.gaierror(-2, 'Name or service not known')
        # `resolves` patched out everywhere these run: a test that performs a
        # real DNS lookup is slow, and fails or passes depending on the
        # network rather than on the code.
        with patch('apps.landing_pages.domain_service.requests.get') as get,                 patch('apps.landing_pages.domain_service.resolves', return_value=False):
            get.side_effect = exc
            result = LandingDomainService.verify(domain)

        self.assertIn('also sends your email', result.last_check_error)
        self.assertIn('use the A record', result.last_check_error)

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


@override_settings(
    PLATFORM_HOSTS=PLATFORM,
    LANDING_DOMAIN_CNAME_TARGET='app.example.com',
    LANDING_DOMAIN_A_TARGET='203.0.113.10',
)
class DnsInstructionTests(TestCase):
    """
    Which record a customer is told to publish.

    A CNAME cannot coexist with any other record at the same name
    (RFC 1034/2181), so on a hostname that already carries records it is
    impossible — not merely discouraged. The first version of this feature
    offered only a CNAME, which meant telling the owner of a sending domain to
    add a record their DNS host would refuse, and then showing them a
    "has it propagated yet" message while they waited for nothing.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.org = Organization.objects.create(name='Alpha', slug='alpha', plan='starter')

    def _domain(self, name):
        return LandingDomain.objects.create(organization=self.org, domain=name)

    def test_a_plain_hostname_is_told_to_use_the_cname(self):
        records = self._domain('go.alpha-example.com').dns_records

        self.assertEqual(records[0]['type'], 'CNAME')
        self.assertTrue(records[0]['recommended'])
        self.assertEqual(records[0]['value'], 'app.example.com')

    def test_an_a_record_is_always_offered_as_well(self):
        types = [r['type'] for r in self._domain('go.alpha-example.com').dns_records]

        self.assertIn('A', types)

    def test_a_sending_domain_is_told_to_use_the_a_record(self):
        """The case that broke: news.soha.systems was already sending email."""
        SendingDomain.objects.create(
            organization=self.org, domain='news.alpha-example.com',
            status=SendingDomain.STATUS_VERIFIED,
        )
        domain = self._domain('news.alpha-example.com')

        records = domain.dns_records

        self.assertTrue(domain.conflicting_sending_domain)
        self.assertEqual(records[0]['type'], 'A')
        self.assertTrue(records[0]['recommended'])
        # And the CNAME is still shown, marked as impossible, rather than
        # hidden — otherwise the reason is invisible.
        cname = next(r for r in records if r['type'] == 'CNAME')
        self.assertFalse(cname['recommended'])
        self.assertIn('cannot coexist', cname['note'])

    def test_a_sending_domain_for_another_tenant_also_conflicts(self):
        """
        DNS does not care which tenant owns the row. If the hostname has email
        records, a CNAME on it is impossible regardless of who added them.
        """
        other = Organization.objects.create(name='Beta', slug='beta')
        SendingDomain.objects.create(organization=other, domain='news.shared.example.com')

        self.assertTrue(self._domain('news.shared.example.com').conflicting_sending_domain)

    def test_the_api_reports_the_conflict(self):
        SendingDomain.objects.create(organization=self.org, domain='news.alpha-example.com')
        user = User.objects.create_user(
            email='owner@alpha.test', password='x', organization=self.org, role='owner',
        )
        api = APIClient()
        api.force_authenticate(user=user)
        self._domain('news.alpha-example.com')

        row = api.get('/api/v1/landing-domains/').data['results'][0]

        self.assertTrue(row['conflicts_with_email'])
        self.assertEqual(row['dns_records'][0]['type'], 'A')

    def test_only_configured_record_types_are_offered(self):
        with override_settings(LANDING_DOMAIN_A_TARGET=''):
            types = [r['type'] for r in self._domain('go.alpha-example.com').dns_records]

        self.assertEqual(types, ['CNAME'])


class DnsFailureClassificationTests(TestCase):
    """
    Telling "does not resolve" apart from "resolves but refuses".

    They have different fixes, and reporting the second for the first is what
    sent someone to wait on propagation of a record that was never accepted.
    """

    def test_a_resolution_failure_is_recognised(self):
        from apps.landing_pages.domain_service import _is_dns_failure

        inner = socket.gaierror(-2, 'Name or service not known')
        exc = requests.exceptions.ConnectionError('wrapped')
        exc.__cause__ = inner

        self.assertTrue(_is_dns_failure(exc))

    def test_a_resolution_failure_is_recognised_from_the_message(self):
        """urllib3 often stringifies the cause rather than chaining it."""
        from apps.landing_pages.domain_service import _is_dns_failure

        exc = requests.exceptions.ConnectionError(
            'HTTPSConnectionPool(host=\'x.test\', port=443): Max retries exceeded '
            '(Caused by NameResolutionError("Failed to resolve \'x.test\'"))'
        )

        self.assertTrue(_is_dns_failure(exc))

    def test_a_refused_connection_is_not_a_resolution_failure(self):
        from apps.landing_pages.domain_service import _is_dns_failure

        exc = requests.exceptions.ConnectionError(
            'HTTPSConnectionPool(host=\'x.test\', port=443): '
            '[Errno 111] Connection refused'
        )

        self.assertFalse(_is_dns_failure(exc))


class HostFieldTests(TestCase):
    """
    What the customer types into their DNS provider's Host field.

    Providers append the zone themselves, so showing the full hostname next to
    a copy button produced `landing.soha.systems.soha.systems` — a record that
    looks correct where it was entered and resolves to nothing.
    """

    def test_the_label_is_split_from_the_zone(self):
        self.assertEqual(split_zone('landing.soha.systems'), ('landing', 'soha.systems'))

    def test_a_deeper_subdomain_keeps_its_full_label(self):
        self.assertEqual(split_zone('go.eu.example.com'), ('go.eu', 'example.com'))

    def test_a_bare_domain_uses_the_apex_marker(self):
        """`@` is what every provider means by "the domain itself"."""
        self.assertEqual(split_zone('example.com'), ('@', 'example.com'))

    @override_settings(
        PLATFORM_HOSTS=PLATFORM,
        LANDING_DOMAIN_CNAME_TARGET='app.example.com',
        LANDING_DOMAIN_A_TARGET='203.0.113.10',
    )
    def test_records_offer_the_label_and_keep_the_full_name_separate(self):
        org = Organization.objects.create(name='Alpha', slug='alpha', plan='starter')
        domain = LandingDomain.objects.create(
            organization=org, domain='landing.alpha-example.com',
        )

        record = domain.dns_records[0]

        self.assertEqual(record['host'], 'landing')
        self.assertEqual(record['full_host'], 'landing.alpha-example.com')
        self.assertEqual(record['zone'], 'alpha-example.com')

    def test_the_doubled_name_is_the_one_a_provider_would_create(self):
        self.assertEqual(
            doubled_name_candidate('landing.soha.systems'),
            'landing.soha.systems.soha.systems',
        )


@override_settings(PLATFORM_HOSTS=PLATFORM)
class DoubledNameDiagnosisTests(TestCase):
    """
    Recognising a record that was saved at the wrong name.

    The generic "no DNS record found" is true and useless here: the customer is
    looking at a record that reads correctly in their provider's UI. Naming the
    mistake is the difference between a fix and another three hours.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.org = Organization.objects.create(name='Alpha', slug='alpha', plan='starter')
        self.domain = LandingDomain.objects.create(
            organization=self.org, domain='landing.alpha-example.com',
        )

    def _verify_with_dns_failure(self):
        exc = requests.exceptions.ConnectionError('boom')
        exc.__cause__ = socket.gaierror(-2, 'Name or service not known')
        with patch('apps.landing_pages.domain_service.requests.get') as get:
            get.side_effect = exc
            return LandingDomainService.verify(self.domain)

    def test_it_names_the_doubled_record_when_that_one_resolves(self):
        with patch('apps.landing_pages.domain_service.resolves') as resolves_mock:
            resolves_mock.return_value = True
            result = self._verify_with_dns_failure()

        self.assertIn(
            'landing.alpha-example.com.alpha-example.com', result.last_check_error,
        )
        self.assertIn('enter just "landing"', result.last_check_error)

    def test_otherwise_it_still_says_which_field_to_correct(self):
        with patch('apps.landing_pages.domain_service.resolves') as resolves_mock:
            resolves_mock.return_value = False
            result = self._verify_with_dns_failure()

        self.assertIn('does not resolve', result.last_check_error)
        self.assertIn('should be "landing"', result.last_check_error)
        self.assertIn('adds "alpha-example.com" itself', result.last_check_error)


@override_settings(PLATFORM_HOSTS=PLATFORM)
class StaleResolverDiagnosisTests(TestCase):
    """
    A correct record that this server cannot see yet.

    Correcting a wrong DNS record runs straight into negative caching: the
    earlier NXDOMAIN is held for the zone's SOA minimum — an hour on many zones
    — so the record is live everywhere except here. Reporting "does not resolve,
    check the Host field" then tells the customer to change the thing they have
    just fixed.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        org = Organization.objects.create(name='Alpha', slug='alpha', plan='starter')
        self.domain = LandingDomain.objects.create(
            organization=org, domain='landing.alpha-example.com',
        )

    def _verify(self, public_answer):
        exc = requests.exceptions.ConnectionError('boom')
        exc.__cause__ = socket.gaierror(-2, 'Name or service not known')
        with patch('apps.landing_pages.domain_service.requests.get') as get, \
                patch('apps.landing_pages.domain_service.resolves', return_value=False), \
                patch(
                    'apps.landing_pages.domain_service.published_publicly',
                    return_value=public_answer,
                ):
            get.side_effect = exc
            return LandingDomainService.verify(self.domain)

    def test_a_publicly_visible_record_is_reported_as_ours_to_wait_for(self):
        result = self._verify(public_answer=True)

        self.assertIn('visible publicly', result.last_check_error)
        self.assertIn('no action needed', result.last_check_error)
        # And it must not tell them to change the Host field they got right.
        self.assertNotIn('should be', result.last_check_error)

    def test_a_genuinely_missing_record_still_says_which_field_to_fix(self):
        result = self._verify(public_answer=False)

        self.assertIn('does not resolve', result.last_check_error)
        self.assertIn('should be "landing"', result.last_check_error)

    def test_an_unknown_public_answer_falls_back_to_the_host_field_advice(self):
        """
        None means the lookup itself failed. Claiming either answer from that
        would be making something up.
        """
        result = self._verify(public_answer=None)

        self.assertIn('does not resolve', result.last_check_error)
