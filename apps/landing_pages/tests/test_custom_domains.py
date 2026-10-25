"""
Serving landing pages on a customer's own hostname.

Production sets `ALLOWED_HOSTS = ['*']` and moves the host check into
`LandingHostMiddleware`, because customers connect domains at runtime and a
settings list cannot express that. That trade is only sound while this file
passes: the middleware has to refuse unknown hosts, and it has to confine a
customer's hostname to landing pages alone. If it is ever removed, reordered
out of first place, or made to fall through, these tests are what notices.
"""
from django.core.cache import cache
from django.middleware.security import SecurityMiddleware
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.landing_pages.models import LandingDomain, LandingPage

PLATFORM = ['localhost', '127.0.0.1', 'testserver', 'backend', 'app.example.com']


@override_settings(ALLOWED_HOSTS=['*'], PLATFORM_HOSTS=PLATFORM)
class CustomDomainServingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.alpha = Organization.objects.create(name='Alpha', slug='alpha')
        self.beta = Organization.objects.create(name='Beta', slug='beta')
        self.alpha_domain = LandingDomain.objects.create(
            organization=self.alpha,
            domain='go.alpha-example.com',
            status=LandingDomain.STATUS_VERIFIED,
        )

    def _page(self, org, slug, **kwargs):
        return LandingPage.objects.create(
            organization=org,
            name=kwargs.pop('name', slug.replace('-', ' ').title()),
            slug=slug,
            status=kwargs.pop('status', 'published'),
            html_content=f'<h1>{org.slug}:{slug}</h1>',
            **kwargs,
        )

    def _get(self, path, host='go.alpha-example.com', **kwargs):
        return self.client.get(path, HTTP_HOST=host, **kwargs)

    # ---------------------------------------------------------- the host gate
    def test_unknown_host_is_refused(self):
        """
        The test the ALLOWED_HOSTS=['*'] trade rests on.

        Without this the production setting is a host-header vulnerability
        rather than a deliberate exchange of one check for a stricter one.
        """
        response = self._get('/', host='attacker.example.com')

        self.assertEqual(response.status_code, 400)

    def test_platform_host_still_serves_the_app(self):
        response = self.client.get('/api/v1/auth/profile/', HTTP_HOST='app.example.com')

        # 401, not 400: the host was accepted and the request reached the API.
        self.assertEqual(response.status_code, 401)

    def test_suspended_organization_stops_serving_immediately(self):
        self._page(self.alpha, 'pricing')
        self.assertEqual(self._get('/pricing/').status_code, 200)

        self.alpha.is_active = False
        self.alpha.save()

        # The lookup is cached for five minutes; a suspension that waited for
        # that to expire would keep a suspended tenant's pages online.
        self.assertEqual(self._get('/pricing/').status_code, 400)

    def test_disconnecting_a_domain_stops_serving_immediately(self):
        self._page(self.alpha, 'pricing')
        self.assertEqual(self._get('/pricing/').status_code, 200)

        self.alpha_domain.delete()

        self.assertEqual(self._get('/pricing/').status_code, 400)

    # ------------------------------------------------------------- what serves
    def test_page_serves_at_the_domain_root_path(self):
        self._page(self.alpha, 'black-friday')

        response = self._get('/black-friday/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('alpha:black-friday', response.content.decode())

    def test_page_serves_without_a_trailing_slash(self):
        """An advert's link will not have one, and a redirect costs a round trip."""
        self._page(self.alpha, 'black-friday')

        self.assertEqual(self._get('/black-friday').status_code, 200)

    def test_domain_root_serves_the_designated_home_page(self):
        self._page(self.alpha, 'other')
        self._page(self.alpha, 'welcome', is_domain_home=True)

        response = self._get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('alpha:welcome', response.content.decode())

    def test_domain_root_404s_without_a_home_page(self):
        self._page(self.alpha, 'pricing')

        self.assertEqual(self._get('/').status_code, 404)

    def test_draft_pages_are_not_served(self):
        self._page(self.alpha, 'secret', status='draft')

        self.assertEqual(self._get('/secret/').status_code, 404)

    # ----------------------------------------------------------- the isolation
    def test_a_domain_never_serves_another_tenants_page(self):
        """
        The hostname names the tenant, so this is structural rather than a
        filter someone has to remember — but it is the whole premise, so it is
        pinned.
        """
        self._page(self.beta, 'pricing')

        self.assertEqual(self._get('/pricing/').status_code, 404)

    def test_a_page_pinned_to_another_domain_is_not_served_here(self):
        second = LandingDomain.objects.create(
            organization=self.alpha,
            domain='promo.alpha-example.com',
            status=LandingDomain.STATUS_VERIFIED,
        )
        self._page(self.alpha, 'pricing', domain=second)

        self.assertEqual(self._get('/pricing/').status_code, 404)
        self.assertEqual(self._get('/pricing/', host='promo.alpha-example.com').status_code, 200)

    # --------------------------------------------- nothing else on that host
    def test_the_api_does_not_exist_on_a_customer_domain(self):
        user = User.objects.create_user(
            email='owner@alpha.test', password='x', organization=self.alpha, role='owner',
        )
        api = APIClient()
        api.force_authenticate(user=user)

        # Authenticated on purpose: a 404 here proves the route is absent
        # rather than merely unauthorized.
        response = api.get('/api/v1/contacts/', HTTP_HOST='go.alpha-example.com')

        self.assertEqual(response.status_code, 404)

    def test_the_admin_does_not_exist_on_a_customer_domain(self):
        self.assertEqual(self._get('/admin/').status_code, 404)

    def test_the_internal_tls_gate_does_not_exist_on_a_customer_domain(self):
        """
        It must be reachable only over the Docker network. Exposed publicly, a
        stranger can enumerate connected domains and burn the ACME quota.
        """
        response = self._get('/internal/tls-allow?domain=go.alpha-example.com')

        self.assertEqual(response.status_code, 404)

    def test_the_platform_route_keeps_working_alongside_a_connected_domain(self):
        self._page(self.alpha, 'pricing')

        response = self.client.get('/p/alpha/pricing/', HTTP_HOST='app.example.com')

        self.assertEqual(response.status_code, 200)


@override_settings(ALLOWED_HOSTS=['*'], PLATFORM_HOSTS=PLATFORM)
class TlsGateTests(TestCase):
    """The endpoint Caddy asks before obtaining a certificate."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.org = Organization.objects.create(name='Alpha', slug='alpha')
        self.domain = LandingDomain.objects.create(
            organization=self.org, domain='go.alpha-example.com',
        )

    def _ask(self, domain):
        return self.client.get(
            '/internal/tls-allow', {'domain': domain}, HTTP_HOST='backend',
        )

    def test_allows_a_connected_domain_even_before_verification(self):
        """
        Safe because ACME requires answering a challenge on that hostname,
        which requires the DNS to already point here. Refusing unverified
        domains instead would deadlock: no certificate, so no verification.
        """
        self.assertEqual(self._ask('go.alpha-example.com').status_code, 200)

    def test_refuses_an_unconnected_domain(self):
        self.assertEqual(self._ask('someone-elses.example.com').status_code, 404)

    def test_refuses_a_suspended_organizations_domain(self):
        self.org.is_active = False
        self.org.save()

        self.assertEqual(self._ask('go.alpha-example.com').status_code, 404)

    def test_refuses_an_empty_domain(self):
        self.assertEqual(self._ask('').status_code, 404)

    def test_allows_the_platform_host(self):
        self.assertEqual(self._ask('app.example.com').status_code, 200)


class TlsGateReachabilityTests(TestCase):
    """
    The gate has to answer Caddy, and Caddy asks over plain HTTP.

    Production sets SECURE_SSL_REDIRECT, which turned that request into a 301.
    Caddy reads anything but 2xx as "refuse", so every customer domain was
    declined a certificate — and nothing else would have shown it, because the
    endpoint answers correctly from everywhere that is not Caddy.
    """

    @override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_REDIRECT_EXEMPT=[r'^internal/tls-allow$'],
    )
    def test_the_gate_is_exempt_from_the_https_redirect(self):
        middleware = SecurityMiddleware(lambda request: None)
        request = RequestFactory().get('/internal/tls-allow', {'domain': 'x.example.com'})

        # None means "no redirect, carry on to the view".
        self.assertIsNone(middleware.process_request(request))

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[])
    def test_without_the_exemption_it_would_be_redirected(self):
        """Pins what the exemption is protecting against, so it is not dropped."""
        middleware = SecurityMiddleware(lambda request: None)
        request = RequestFactory().get('/internal/tls-allow', {'domain': 'x.example.com'})

        self.assertEqual(middleware.process_request(request).status_code, 301)

    def test_production_configures_the_exemption(self):
        from config.settings import production

        self.assertIn(r'^internal/tls-allow$', production.SECURE_REDIRECT_EXEMPT)
