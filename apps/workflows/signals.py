"""
Signal handlers for workflow triggers.
Connects various events to workflow execution.
"""
import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


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
