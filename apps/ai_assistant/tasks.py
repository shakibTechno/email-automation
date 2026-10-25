"""
Celery tasks for the AI Assistant app.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def run_generation(self, job_id: str):
    """
    Run one generation, of whatever kind.

    No retries: generation spends the customer's own tokens, so a failed run
    must not silently become three. The user retries from the UI.
    """
    from apps.ai_assistant.models import GenerationJob
    from apps.ai_assistant.services import GenerationService

    try:
        job = GenerationJob.objects.select_related('organization').get(pk=job_id)
    except GenerationJob.DoesNotExist:
        logger.warning(f'Generation job {job_id} not found')
        return

    GenerationService.run(job)


#: The landing-page-only name this task had before it learned other kinds.
generate_landing_page = run_generation
