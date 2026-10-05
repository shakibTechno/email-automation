"""
Celery tasks for the Contact Segmentation app.
"""
import logging
from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task
def refresh_segment_count(segment_id: str):
    """
    Refresh the contact count for a single segment.

    Args:
        segment_id: UUID of the segment
    """
    from .models import Segment
    from .services import SegmentService

    try:
        segment = Segment.objects.get(id=segment_id)
        count = SegmentService.refresh_segment_count(segment)
        logger.info(f"Refreshed segment '{segment.name}': {count} contacts")
        return count
    except Segment.DoesNotExist:
        logger.warning(f"Segment {segment_id} not found")
        return None


@shared_task
def refresh_all_organization_segments(organization_id: str):
    """
    Refresh contact counts for all segments in an organization.

    Args:
        organization_id: UUID of the organization
    """
    from apps.accounts.models import Organization
    from .services import SegmentService

    try:
        organization = Organization.objects.get(id=organization_id)
        count = SegmentService.refresh_all_segment_counts(organization)
        logger.info(f"Refreshed {count} segments for organization '{organization.name}'")
        return count
    except Organization.DoesNotExist:
        logger.warning(f"Organization {organization_id} not found")
        return None


@shared_task
def refresh_all_dynamic_segments():
    """
    Refresh contact counts for all dynamic segments across all organizations.
    Typically scheduled to run periodically (e.g., every hour).
    """
    from .models import Segment
    from .services import SegmentService

    segments = Segment.objects.filter(segment_type='dynamic')
    refreshed = 0
    errors = 0

    for segment in segments:
        try:
            SegmentService.refresh_segment_count(segment)
            refreshed += 1
        except Exception as e:
            logger.error(f"Error refreshing segment {segment.id}: {e}")
            errors += 1

    logger.info(f"Segment refresh complete: {refreshed} refreshed, {errors} errors")
    return {'refreshed': refreshed, 'errors': errors}


@shared_task
def export_segment_async(segment_id: str, user_id: str = None):
    """
    Export segment contacts asynchronously.
    Can be used for large segments to avoid request timeout.

    Args:
        segment_id: UUID of the segment
        user_id: UUID of the user who requested the export (for notification)

    Returns:
        CSV content as string
    """
    from .models import Segment
    from .services import SegmentService

    try:
        segment = Segment.objects.get(id=segment_id)
        csv_content = SegmentService.export_segment_contacts_csv(segment)
        logger.info(f"Exported segment '{segment.name}' ({segment.contact_count} contacts)")

        # TODO: Could save to file storage and send notification email to user
        # For now, just return the content
        return {
            'segment_id': str(segment_id),
            'segment_name': segment.name,
            'contact_count': segment.contact_count,
            'csv_length': len(csv_content),
        }
    except Segment.DoesNotExist:
        logger.warning(f"Segment {segment_id} not found")
        return None
