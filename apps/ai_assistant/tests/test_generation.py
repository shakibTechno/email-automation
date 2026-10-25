"""
Job lifecycle tests, driven by a stubbed provider.

These deliberately never touch a real API: they prove the plumbing around the
provider boundary — queue, sanitize, create page, record usage, and fail
without leaving a half-made draft.
"""
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import Organization, User
from apps.ai_assistant.models import AIConfiguration, GenerationJob
from apps.ai_assistant.providers import AIAuthError, AIError
from apps.ai_assistant.generators import landing_pages
from apps.ai_assistant.services import GenerationService
from apps.landing_pages.models import LandingPage

GOOD_HTML = (
    '<section class="py-16 px-4"><div class="max-w-6xl mx-auto">'
    '<h1 class="text-4xl font-bold">A real heading</h1></div></section>'
)


class StubProvider:
    """Stands in for a vendor adapter."""

    model = 'stub-model-1'

    def __init__(self, payload=None, error=None):
        self._payload = payload or {
            'name': 'Generated Page',
            'seo_title': 'Generated Page',
            'seo_description': 'A page made by the stub.',
            'html': GOOD_HTML,
        }
        self._error = error

    def generate_json(self, *, system, user, schema):
        if self._error:
            raise self._error
        return self._payload, {'input_tokens': 1200, 'output_tokens': 3400}


class GenerationTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Probe Org', slug='probe-org')
        self.user = User.objects.create_user(
            email='probe@example.com', password='x', organization=self.org,
        )
        AIConfiguration.objects.create(
            organization=self.org, provider='anthropic',
            api_key='sk-test-not-a-real-key', is_enabled=True,
        )

    def _job(self, prompt='A landing page for a yoga studio in Bristol'):
        return GenerationJob.objects.create(
            organization=self.org, created_by=self.user, prompt=prompt,
        )

    def _run_with(self, provider):
        with patch(
            'apps.ai_assistant.services.AIConfigService.build_provider',
            return_value=provider,
        ):
            return GenerationService.run(self._job())

    def test_successful_run_creates_a_draft_page(self):
        job = self._run_with(StubProvider())

        self.assertEqual(job.status, GenerationJob.STATUS_SUCCEEDED)
        self.assertIsNotNone(job.landing_page)

        page = job.landing_page
        self.assertEqual(page.status, 'draft')
        self.assertEqual(page.organization, self.org)
        self.assertIn('A real heading', page.html_content)
        self.assertEqual(page.seo_title, 'Generated Page')
        # Empty design_json is what makes the builder import the HTML as
        # editable components rather than loading a saved project.
        self.assertEqual(page.design_json, {})

    def test_records_token_usage(self):
        job = self._run_with(StubProvider())
        self.assertEqual(job.input_tokens, 1200)
        self.assertEqual(job.output_tokens, 3400)
        self.assertEqual(job.model, 'stub-model-1')

    def test_dangerous_markup_never_reaches_the_page(self):
        job = self._run_with(StubProvider(payload={
            'name': 'Sneaky', 'seo_title': 'S', 'seo_description': 'd',
            'html': GOOD_HTML + '<script>steal()</script>',
        }))

        self.assertEqual(job.status, GenerationJob.STATUS_SUCCEEDED)
        self.assertNotIn('<script', job.landing_page.html_content)
        self.assertTrue(job.was_sanitized)

    def test_provider_failure_leaves_no_page_behind(self):
        job = self._run_with(StubProvider(error=AIAuthError('Key rejected.')))

        self.assertEqual(job.status, GenerationJob.STATUS_FAILED)
        self.assertEqual(job.error_message, 'Key rejected.')
        self.assertIsNone(job.landing_page)
        self.assertEqual(LandingPage.objects.filter(organization=self.org).count(), 0)

    def test_empty_markup_is_a_failure_not_an_empty_page(self):
        job = self._run_with(StubProvider(payload={
            'name': 'Nothing', 'seo_title': '', 'seo_description': '', 'html': '',
        }))

        self.assertEqual(job.status, GenerationJob.STATUS_FAILED)
        self.assertEqual(LandingPage.objects.filter(organization=self.org).count(), 0)

    def test_runs_without_a_connected_provider_fail_cleanly(self):
        AIConfiguration.objects.filter(organization=self.org).update(is_enabled=False)
        job = GenerationService.run(self._job())

        self.assertEqual(job.status, GenerationJob.STATUS_FAILED)
        self.assertIn('Settings', job.error_message)
        self.assertEqual(LandingPage.objects.filter(organization=self.org).count(), 0)

    def test_overlong_model_metadata_is_truncated_not_rejected(self):
        job = self._run_with(StubProvider(payload={
            'name': 'N' * 400,
            'seo_title': 'T' * 200,
            'seo_description': 'D' * 400,
            'html': GOOD_HTML,
        }))

        self.assertEqual(job.status, GenerationJob.STATUS_SUCCEEDED)
        self.assertLessEqual(len(job.landing_page.name), 255)
        self.assertLessEqual(len(job.landing_page.seo_title), 70)
        self.assertLessEqual(len(job.landing_page.seo_description), 160)


class ConfigSerializerTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Key Org', slug='key-org')

    def test_api_key_is_never_serialized_back(self):
        from apps.ai_assistant.serializers import AIConfigurationSerializer

        config = AIConfiguration.objects.create(
            organization=self.org, api_key='sk-secret-value',
        )
        data = AIConfigurationSerializer(config).data

        self.assertNotIn('api_key', data)
        self.assertTrue(data['api_key_set'])
        self.assertNotIn('sk-secret-value', str(data))

    def test_blank_key_on_update_preserves_the_stored_one(self):
        from apps.ai_assistant.serializers import AIConfigurationUpdateSerializer

        config = AIConfiguration.objects.create(
            organization=self.org, api_key='sk-original',
        )
        serializer = AIConfigurationUpdateSerializer(
            config, data={'api_key': '', 'is_enabled': True}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        config = serializer.save()

        self.assertEqual(config.api_key, 'sk-original')
        self.assertTrue(config.is_enabled)

    def test_a_new_key_clears_the_previous_validation(self):
        from django.utils import timezone

        from apps.ai_assistant.serializers import AIConfigurationUpdateSerializer

        config = AIConfiguration.objects.create(
            organization=self.org, api_key='sk-old',
            last_validated_at=timezone.now(),
        )
        serializer = AIConfigurationUpdateSerializer(
            config, data={'api_key': 'sk-new'}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        config = serializer.save()

        self.assertEqual(config.api_key, 'sk-new')
        self.assertIsNone(config.last_validated_at)


class SelfHostedProviderTests(TestCase):
    """
    A self-hosted server is reached by address, not by credential, so the
    readiness rules that apply to a hosted provider must not apply here.
    """

    def setUp(self):
        self.org = Organization.objects.create(name='Local Org', slug='local-org')

    def test_is_ready_without_an_api_key(self):
        config = AIConfiguration.objects.create(
            organization=self.org, provider='local',
            base_url='http://192.168.0.2:8080', is_enabled=True,
        )
        self.assertTrue(config.is_ready)

    def test_not_ready_without_an_address(self):
        config = AIConfiguration.objects.create(
            organization=self.org, provider='local', is_enabled=True,
        )
        self.assertFalse(config.is_ready)

    def test_hosted_provider_still_needs_a_key(self):
        config = AIConfiguration.objects.create(
            organization=self.org, provider='anthropic',
            base_url='http://192.168.0.2:8080', is_enabled=True,
        )
        self.assertFalse(config.is_ready)

    def test_serializer_reports_that_no_key_is_required(self):
        from apps.ai_assistant.serializers import AIConfigurationSerializer

        config = AIConfiguration.objects.create(
            organization=self.org, provider='local',
            base_url='http://192.168.0.2:8080',
        )
        data = AIConfigurationSerializer(config).data
        self.assertFalse(data['requires_api_key'])
        self.assertEqual(data['base_url'], 'http://192.168.0.2:8080')


class FormSlotTests(TestCase):
    """
    A page with no capture point cannot convert anyone, and smaller models do
    not reliably follow the instruction to leave one.
    """

    def test_slot_is_added_when_the_model_omits_it(self):
        html = landing_pages.ensure_form_slot(GOOD_HTML)
        self.assertIn('data-form-slot', html)
        self.assertIn('A real heading', html)

    def test_existing_slot_is_left_alone(self):
        source = GOOD_HTML + '<div data-form-slot="true">here</div>'
        self.assertEqual(landing_pages.ensure_form_slot(source), source)

    def test_empty_markup_is_not_given_a_slot(self):
        """Empty output is a failure, not a page that needs a form."""
        self.assertEqual(landing_pages.ensure_form_slot(''), '')
