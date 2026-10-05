"""
Celery tasks for the Email Sequences app.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def process_sequence_enrollments():
    """Process all due sequence step sends. Runs every minute via Celery Beat."""
    from .services import SequenceEnrollmentService
    try:
        count = SequenceEnrollmentService.process_due_enrollments()
        if count:
            logger.info(f"Processed {count} sequence enrollments")
        return count
    except Exception as exc:
        logger.exception(f"Error processing sequence enrollments: {exc}")
        return 0
