"""
Signals for the billing app.

Loaded by BillingConfig.ready().
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='accounts.Organization')
def create_subscription_for_new_organization(sender, instance, created, **kwargs):
    """
    Give every new organization a free-plan subscription.

    BillingService.initialize_subscription() existed but had no callers, so
    organizations registered with no Subscription row at all: billing endpoints
    returned 404, and check_usage_limit() answered
    {'allowed': False, 'reason': 'No active subscription'} — which would block
    every send the moment quota enforcement was switched on.

    A signal rather than a call inside RegisterSerializer.create(), because
    organizations are also created by the setup_initial_data command and by any
    future path; the serializer would only cover one of them.

    Failures are logged, never raised. An organization without a subscription
    can be repaired by the backfill command; an organization that fails to be
    created at all cannot.
    """
    if not created:
        return

    from .services import BillingService

    try:
        BillingService.initialize_subscription(instance, instance.email or '')
    except Exception:
        logger.exception(
            'Could not initialize a subscription for organization %s; '
            'run `manage.py backfill_subscriptions` to repair it',
            instance.pk,
        )
