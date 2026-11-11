"""
Signal handlers for workflow triggers.
Connects various events to workflow execution.
"""
import logging

from django.core.cache import cache
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Contact fields worth comparing across a save. Everything a marketer
# plausibly triggers on, and nothing that churns on every send -- watching
# last_activity_at here would fire a workflow on its own tracking pixel.
WATCHED_CONTACT_FIELDS = (
    'is_subscribed', 'lifecycle_stage', 'lead_source', 'company', 'job_title',
    'city', 'country', 'assigned_to_id', 'engagement_level', 'external_id',
)

# Taking the "before" picture costs a query on every contact save, so it is
# only taken by accounts that have a workflow waiting for one. Cached for a
# minute, which is also how long a newly activated workflow takes to start
# noticing changes.
_WATCH_FLAG_SECONDS = 60


def _organization_watches_changes(organization_id):
    key = f'wf:watch-contact:{organization_id}'
    cached = cache.get(key)
    if cached is not None:
        return cached

    from .models import Workflow, WorkflowNode

    watching = Workflow.objects.filter(
        organization_id=organization_id,
        status='active',
        deleted_at__isnull=True,
        nodes__node_type__in=(
            WorkflowNode.TRIGGER_CONTACT_FIELD_CHANGED,
            WorkflowNode.TRIGGER_EMAIL_UNSUBSCRIBED,
        ),
    ).exists()
    cache.set(key, watching, _WATCH_FLAG_SECONDS)
    return watching


@receiver(post_save, sender='forms.FormSubmission')
def on_form_submission(sender, instance, created, **kwargs):
    """Trigger workflows when a form submission is created."""
    if not created:
        return

    # Avoid import at module level to prevent circular imports
    from .services import WorkflowTriggerService

    if instance.contact and instance.form:
        try:
            WorkflowTriggerService.trigger_form_submission(
                form=instance.form,
                contact=instance.contact,
                submission=instance,
            )
        except Exception as e:
            logger.exception(f"Error triggering form submission workflow: {e}")


@receiver(post_save, sender='contacts.ContactTag')
def on_tag_added(sender, instance, created, **kwargs):
    """Trigger workflows when a tag is added to a contact."""
    if not created:
        return

    from .services import WorkflowTriggerService

    try:
        WorkflowTriggerService.trigger_tag_added(
            contact=instance.contact,
            tag=instance.tag,
        )
    except Exception as e:
        logger.exception(f"Error triggering tag added workflow: {e}")


@receiver(pre_delete, sender='contacts.ContactTag')
def on_tag_removed(sender, instance, **kwargs):
    """Trigger workflows when a tag is removed from a contact."""
    from .services import WorkflowTriggerService

    try:
        WorkflowTriggerService.trigger_tag_removed(
            contact=instance.contact,
            tag=instance.tag,
        )
    except Exception as e:
        logger.exception(f"Error triggering tag removed workflow: {e}")


@receiver(post_save, sender='contacts.Contact')
def on_contact_created(sender, instance, created, **kwargs):
    """Trigger workflows when a new contact is created."""
    if not created:
        return

    from .services import WorkflowTriggerService

    try:
        WorkflowTriggerService.trigger_contact_created(contact=instance)
    except Exception as e:
        logger.exception(f"Error triggering contact created workflow: {e}")


@receiver(pre_save, sender='contacts.Contact')
def snapshot_contact(sender, instance, **kwargs):
    """Remember the values a field-changed trigger might care about."""
    if not instance.pk:
        return
    if not _organization_watches_changes(instance.organization_id):
        instance._workflow_before = None
        return

    from apps.contacts.models import Contact

    before = (
        Contact.objects.filter(pk=instance.pk)
        .values(*WATCHED_CONTACT_FIELDS)
        .first()
    )
    instance._workflow_before = before


@receiver(post_save, sender='contacts.Contact')
def on_contact_changed(sender, instance, created, **kwargs):
    """Fire field-changed and unsubscribed for whatever actually moved."""
    if created:
        return

    before = getattr(instance, '_workflow_before', None)
    if not before:
        return

    from .services import WorkflowTriggerService

    for field in WATCHED_CONTACT_FIELDS:
        was, now = before.get(field), getattr(instance, field, None)
        if was == now:
            continue

        try:
            if field == 'is_subscribed' and was and not now:
                WorkflowTriggerService.trigger_email_unsubscribed(instance)
            WorkflowTriggerService.trigger_contact_field_changed(
                contact=instance, field=field, old_value=was, new_value=now,
            )
        except Exception:
            logger.exception(
                'Error triggering workflows for %s change on contact %s',
                field, instance.pk,
            )


@receiver(post_save, sender='sequences.SequenceEnrollment')
def on_sequence_enrollment_saved(sender, instance, created, **kwargs):
    """
    Fire when a contact reaches the end of a sequence.

    A signal rather than two calls inside SequenceService: the enrollment is
    completed in two different places there, and a hook on the model cannot
    miss one of them the way a hand-placed call can.
    """
    if created or instance.status != 'completed':
        return

    # The status is set alongside completed_at in a single save, so this runs
    # once per enrollment rather than on every later touch.
    if 'status' not in (kwargs.get('update_fields') or ['status']):
        return

    from .services import WorkflowTriggerService

    try:
        WorkflowTriggerService.trigger_sequence_completed(instance)
    except Exception:
        logger.exception(
            'Error triggering sequence-completed workflows for %s', instance.pk
        )
