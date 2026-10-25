"""
Celery tasks for lead scoring.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def recalculate_contact_score(self, contact_id: str):
    """
    Re-evaluate all demographic rules for a single contact.
    Triggered by the post_save signal on Contact when demographic fields change.
    """
    from apps.contacts.models import Contact
    from apps.lead_scoring.services import LeadScoringService

    try:
        contact = Contact.objects.select_related('organization').get(pk=contact_id)
        LeadScoringService.recalculate_contact(contact)
    except Contact.DoesNotExist:
        logger.warning(f"Contact {contact_id} not found for score recalculation")
    except Exception as exc:
        logger.exception(f"Error recalculating score for contact {contact_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def apply_behavioral_score(self, contact_id: str, rule_id: str):
    """
    Apply a single behavioral scoring rule to a contact.
    Triggered immediately when the matching event fires.
    """
    from apps.contacts.models import Contact
    from apps.lead_scoring.models import ScoringRule
    from apps.lead_scoring.services import LeadScoringService

    try:
        contact = Contact.objects.select_related('organization').get(pk=contact_id)
        rule = ScoringRule.objects.get(pk=rule_id, is_active=True, deleted_at__isnull=True)
        LeadScoringService.apply_behavioral_rule(contact, rule)
    except (Contact.DoesNotExist, ScoringRule.DoesNotExist) as e:
        logger.warning(f"Object not found for behavioral score: {e}")
    except Exception as exc:
        logger.exception(
            f"Error applying behavioral rule {rule_id} to contact {contact_id}: {exc}"
        )
        raise self.retry(exc=exc)


@shared_task
def bulk_recalculate_organization(organization_id: str):
    """
    Re-evaluate demographic rules for all contacts in one organization.
    Called by the periodic coordinator task.
    """
    from apps.accounts.models import Organization
    from apps.lead_scoring.services import LeadScoringService

    try:
        org = Organization.objects.get(pk=organization_id)
        updated = LeadScoringService.bulk_recalculate(org)
        logger.info(
            f"Bulk recalculation for org {org.name}: {updated} contacts updated"
        )
    except Organization.DoesNotExist:
        logger.warning(f"Organization {organization_id} not found for bulk recalculation")
    except Exception as e:
        logger.exception(f"Error in bulk recalculation for org {organization_id}: {e}")


@shared_task
def periodic_bulk_recalculate_all_orgs():
    """
    Daily coordinator: fires bulk_recalculate_organization for every
    Professional+ org.  Runs at 03:00 UTC via Celery Beat.
    """
    from apps.accounts.models import Organization
    from apps.lead_scoring.permissions import LEAD_SCORING_MIN_PLAN

    # Derived from the same rank the permission class uses, so this cannot
    # drift from it. It previously filtered on a hardcoded tuple that omitted
    # Business, meaning those organizations passed the API permission check but
    # were skipped by the nightly recalculation — their scores silently went
    # stale while the feature appeared to be enabled.
    eligible = [
        plan for plan, rank in Organization.PLAN_RANK.items()
        if rank >= Organization.PLAN_RANK[LEAD_SCORING_MIN_PLAN]
    ]

    orgs = Organization.objects.filter(
        plan__in=eligible,
        is_active=True,
        deleted_at__isnull=True,
    ).values_list('id', flat=True)

    count = 0
    for org_id in orgs:
        bulk_recalculate_organization.delay(str(org_id))
        count += 1

    logger.info(f"Queued bulk recalculation for {count} organizations")
