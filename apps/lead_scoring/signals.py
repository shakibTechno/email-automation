"""
Signal handlers that hook into existing events to fire lead scoring tasks.

Anti-loop guard: LeadScoringService saves contacts with exactly
    update_fields={'lead_score', 'engagement_level', 'updated_at'}
The on_contact_field_changed handler skips when it detects this set,
preventing the service write from re-triggering recalculation.

All handlers are wrapped in try/except so scoring never disrupts
the primary event (e.g., form submissions, tag operations).
"""
import logging
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from apps.lead_scoring.services import SCORE_UPDATE_FIELDS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: find and queue matching behavioral rules
# ---------------------------------------------------------------------------

def _fire_behavioral_rules(contact, event_type: str, event_filter: dict = None):
    """Queue apply_behavioral_score tasks for all active rules matching the event."""
    from apps.lead_scoring.models import ScoringRule
    from apps.lead_scoring.tasks import apply_behavioral_score

    rules = ScoringRule.objects.filter(
        organization=contact.organization,
        rule_type=ScoringRule.RULE_TYPE_BEHAVIORAL,
        event_type=event_type,
        is_active=True,
        deleted_at__isnull=True,
    )

    for rule in rules:
        if event_filter and rule.event_filter:
            # Check that every key in rule.event_filter matches event_filter
            if not all(
                rule.event_filter.get(k) == v for k, v in rule.event_filter.items()
                if k in event_filter
            ):
                continue
        apply_behavioral_score.delay(str(contact.id), str(rule.id))


# ---------------------------------------------------------------------------
# CampaignRecipient — email opened / clicked
# ---------------------------------------------------------------------------

@receiver(pre_save, sender='campaigns.CampaignRecipient')
def _cache_recipient_pre_save(sender, instance, **kwargs):
    """Cache previous opened_at/clicked_at so post_save can detect changes."""
    if instance.pk:
        try:
            prev = sender.objects.get(pk=instance.pk)
            instance._pre_opened_at = prev.opened_at
            instance._pre_clicked_at = prev.clicked_at
        except sender.DoesNotExist:
            instance._pre_opened_at = None
            instance._pre_clicked_at = None
    else:
        instance._pre_opened_at = None
        instance._pre_clicked_at = None


@receiver(post_save, sender='campaigns.CampaignRecipient')
def on_campaign_recipient_updated(sender, instance, created, **kwargs):
    """Fire behavioral scoring when an email is first opened or clicked."""
    if created:
        return

    contact = getattr(instance, 'contact', None)
    if not contact:
        return

    try:
        # Detect first open
        pre_opened = getattr(instance, '_pre_opened_at', None)
        if instance.opened_at and not pre_opened:
            _fire_behavioral_rules(contact, 'email_opened')

        # Detect first click
        pre_clicked = getattr(instance, '_pre_clicked_at', None)
        if instance.clicked_at and not pre_clicked:
            _fire_behavioral_rules(contact, 'email_clicked')
    except Exception as e:
        logger.exception(f"Error in lead scoring signal (campaign_recipient): {e}")

    # The same two transitions drive workflows. WorkflowTriggerService has had
    # trigger_email_opened and trigger_email_clicked since it was written and
    # nothing has ever called them, so the "Email Opened" trigger the builder
    # offers has never fired for anybody. This is the call that was missing.
    try:
        from apps.workflows.services import WorkflowTriggerService

        if instance.opened_at and not getattr(instance, '_pre_opened_at', None):
            WorkflowTriggerService.trigger_email_opened(instance)
        if instance.clicked_at and not getattr(instance, '_pre_clicked_at', None):
            WorkflowTriggerService.trigger_email_clicked(instance)
    except Exception as e:
        logger.exception(f"Error firing email workflows: {e}")


# ---------------------------------------------------------------------------
# FormSubmission — form submitted
# ---------------------------------------------------------------------------

@receiver(post_save, sender='forms.FormSubmission')
def on_form_submission_created(sender, instance, created, **kwargs):
    """Fire behavioral scoring when a form is submitted."""
    if not created:
        return

    contact = getattr(instance, 'contact', None)
    if not contact:
        return

    try:
        _fire_behavioral_rules(
            contact,
            'form_submitted',
            {'form_id': str(instance.form_id)} if instance.form_id else {},
        )
    except Exception as e:
        logger.exception(f"Error in lead scoring signal (form_submission): {e}")


# ---------------------------------------------------------------------------
# ContactTag — tag added / removed
# ---------------------------------------------------------------------------

@receiver(post_save, sender='contacts.ContactTag')
def on_contact_tag_added(sender, instance, created, **kwargs):
    """Fire behavioral scoring when a tag is added to a contact."""
    if not created:
        return

    try:
        _fire_behavioral_rules(
            instance.contact,
            'tag_added',
            {'tag_id': str(instance.tag_id)},
        )
    except Exception as e:
        logger.exception(f"Error in lead scoring signal (tag_added): {e}")


@receiver(pre_delete, sender='contacts.ContactTag')
def on_contact_tag_removed(sender, instance, **kwargs):
    """Fire behavioral scoring when a tag is removed from a contact."""
    try:
        _fire_behavioral_rules(
            instance.contact,
            'tag_removed',
            {'tag_id': str(instance.tag_id)},
        )
    except Exception as e:
        logger.exception(f"Error in lead scoring signal (tag_removed): {e}")


# ---------------------------------------------------------------------------
# WorkflowExecution — workflow completed
# ---------------------------------------------------------------------------

@receiver(pre_save, sender='workflows.WorkflowExecution')
def _cache_execution_pre_save(sender, instance, **kwargs):
    """Cache previous execution status for post_save comparison."""
    if instance.pk:
        try:
            prev = sender.objects.get(pk=instance.pk)
            instance._pre_status = prev.status
        except sender.DoesNotExist:
            instance._pre_status = None
    else:
        instance._pre_status = None


@receiver(post_save, sender='workflows.WorkflowExecution')
def on_workflow_execution_completed(sender, instance, created, **kwargs):
    """Fire behavioral scoring when a workflow execution completes."""
    if created:
        return

    pre_status = getattr(instance, '_pre_status', None)
    if instance.status == 'completed' and pre_status != 'completed':
        contact = getattr(instance, 'contact', None)
        if not contact:
            return
        try:
            _fire_behavioral_rules(contact, 'workflow_completed')
        except Exception as e:
            logger.exception(f"Error in lead scoring signal (workflow_completed): {e}")


# ---------------------------------------------------------------------------
# Contact — unsubscribed / bounced / field changes
# ---------------------------------------------------------------------------

@receiver(pre_save, sender='contacts.Contact')
def _cache_contact_pre_save(sender, instance, **kwargs):
    """Cache is_subscribed and bounced_at for post_save comparison."""
    if instance.pk:
        try:
            prev = sender.objects.get(pk=instance.pk)
            instance._pre_is_subscribed = prev.is_subscribed
            instance._pre_bounced_at = prev.bounced_at
        except sender.DoesNotExist:
            instance._pre_is_subscribed = None
            instance._pre_bounced_at = None
    else:
        instance._pre_is_subscribed = None
        instance._pre_bounced_at = None


@receiver(post_save, sender='contacts.Contact')
def on_contact_saved(sender, instance, created, **kwargs):
    """
    Handle contact field changes:
      1. Unsubscribed event
      2. Bounced event
      3. Demographic recalculation (when non-score fields change)
    """
    from apps.lead_scoring.tasks import recalculate_contact_score

    update_fields = kwargs.get('update_fields')

    # Convert frozenset/None to a comparable set
    if update_fields is not None:
        update_fields_set = set(update_fields)
    else:
        update_fields_set = None

    # Anti-loop guard: skip if the service itself wrote these fields
    if update_fields_set == SCORE_UPDATE_FIELDS:
        return

    try:
        # Detect unsubscribe transition
        pre_subscribed = getattr(instance, '_pre_is_subscribed', None)
        if (
            not created
            and not instance.is_subscribed
            and pre_subscribed is True
        ):
            _fire_behavioral_rules(instance, 'unsubscribed')

        # Detect first bounce
        pre_bounced = getattr(instance, '_pre_bounced_at', None)
        if instance.bounced_at and pre_bounced is None:
            _fire_behavioral_rules(instance, 'bounced')

        # Queue demographic recalculation (skip on new contacts — no rules to match yet)
        if not created:
            recalculate_contact_score.delay(str(instance.pk))
    except Exception as e:
        logger.exception(f"Error in lead scoring signal (contact_saved): {e}")
