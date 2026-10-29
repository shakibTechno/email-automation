"""
Services for the AI Assistant app.
"""
import logging

from django.utils import timezone

from .models import AIConfiguration, GenerationJob
from .providers import AIError, get_provider

logger = logging.getLogger(__name__)


class AIConfigService:
    """Reading and testing an organization's LLM connection."""

    @staticmethod
    def get_or_create(organization) -> AIConfiguration:
        config, _ = AIConfiguration.objects.get_or_create(organization=organization)
        return config

    @staticmethod
    def build_provider(config: AIConfiguration):
        """The configured adapter, ready to call."""
        return get_provider(
            config.provider, config.api_key, config.model, config.base_url,
        )

    @staticmethod
    def test_connection(config: AIConfiguration) -> tuple[bool, str]:
        """
        Check the stored credentials, recording the outcome on the config.

        Returns ``(ok, message)``; never raises, because this sits behind a
        button and a failure is an answer, not an error.
        """
        # Deliberately not `is_ready`, which also requires the feature to be
        # switched on: testing the connection before enabling it is the normal
        # order to do things in.
        if config.provider in AIConfiguration.SELF_HOSTED_PROVIDERS:
            if not config.base_url:
                return False, 'No server address saved yet.'
        elif not config.api_key:
            return False, 'No API key saved yet.'

        try:
            AIConfigService.build_provider(config).validate()
        except AIError as exc:
            config.last_error = exc.message
            config.save(update_fields=['last_error', 'updated_at'])
            return False, exc.message
        except Exception as exc:  # pragma: no cover - unexpected SDK failure
            logger.exception('Unexpected error validating AI credentials')
            config.last_error = str(exc)
            config.save(update_fields=['last_error', 'updated_at'])
            return False, 'Could not reach the provider. Check the server logs.'

        config.last_validated_at = timezone.now()
        config.last_error = ''
        config.save(update_fields=['last_validated_at', 'last_error', 'updated_at'])
        return True, 'Connection successful.'


def _generator_for(kind: str):
    """
    The module that knows how to build one kind of thing.

    Imported lazily so a generator that touches another app's models cannot
    create an import cycle at startup.
    """
    from .generators import email_templates, forms, landing_pages

    try:
        return {
            GenerationJob.KIND_LANDING_PAGE: landing_pages,
            GenerationJob.KIND_FORM: forms,
            GenerationJob.KIND_EMAIL_TEMPLATE: email_templates,
        }[kind]
    except KeyError:
        raise AIError(f'Nothing knows how to generate "{kind}".') from None


class GenerationService:
    """
    Running one generation, of whatever kind.

    The shape is the same every time — ask the provider for JSON matching a
    schema, then hand the payload to the generator that knows what to build
    from it — so adding a kind means adding a module, not a branch here.
    """

    @staticmethod
    def run(job: GenerationJob) -> GenerationJob:
        """
        Execute one job to completion.

        The result is created only once there is something usable to create it
        from, so a failure leaves nothing half-made behind.
        """
        config = AIConfiguration.objects.filter(organization=job.organization).first()
        if config is None or not config.is_ready:
            return GenerationService._fail(
                job, 'No AI provider is connected. Add a key in Settings → AI.'
            )

        try:
            generator = _generator_for(job.kind)
        except AIError as exc:
            return GenerationService._fail(job, exc.message)

        job.status = GenerationJob.STATUS_RUNNING
        job.started_at = timezone.now()
        job.provider = config.provider
        job.save(update_fields=['status', 'started_at', 'provider', 'updated_at'])

        try:
            provider = AIConfigService.build_provider(config)
            payload, usage = provider.generate_json(
                system=generator.SYSTEM_PROMPT,
                user=generator.build_user_prompt(
                    prompt=job.prompt, audience=job.audience,
                ),
                schema=generator.SCHEMA,
            )
        except AIError as exc:
            return GenerationService._fail(job, exc.message)
        except Exception:  # pragma: no cover - unexpected SDK failure
            logger.exception('Unexpected error during generation')
            return GenerationService._fail(
                job, 'Generation failed unexpectedly. Check the server logs.'
            )

        # Read after the call: a self-hosted provider discovers which model the
        # server has loaded as part of making the request, so reading this
        # beforehand recorded an empty string.
        job.model = provider.model
        job.input_tokens = usage.get('input_tokens', 0)
        job.output_tokens = usage.get('output_tokens', 0)

        # Generators may clean the payload before it is judged usable; those
        # that need neither step simply do not define the hooks.
        was_sanitized = False
        if hasattr(generator, 'prepare'):
            payload, was_sanitized = generator.prepare(payload)
        if hasattr(generator, 'validate'):
            problem = generator.validate(payload)
            if problem:
                return GenerationService._fail(job, problem)

        try:
            result = generator.create(job, payload)
        except Exception:
            logger.exception(f'Failed to build {job.kind} from a generated payload')
            return GenerationService._fail(
                job, "The model's output could not be turned into something usable."
            )

        setattr(job, job.kind, result)
        job.was_sanitized = was_sanitized
        job.status = GenerationJob.STATUS_SUCCEEDED
        job.finished_at = timezone.now()
        job.save()
        logger.info(f'Job {job.id} generated {job.kind} {result.id}')
        return job

    @staticmethod
    def _fail(job: GenerationJob, message: str) -> GenerationJob:
        job.status = GenerationJob.STATUS_FAILED
        job.error_message = message
        job.finished_at = timezone.now()
        job.save()
        logger.warning(f'Generation job {job.id} failed: {message}')
        return job


#: The landing-page-only name this service had before it learned other kinds.
PageGenerationService = GenerationService
