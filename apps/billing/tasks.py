"""
Celery tasks for the billing app.
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def check_trial_expirations():
    """Check and expire trials that have ended."""
    from .models import Subscription, Plan
    from .services import BillingEvent

    expired_trials = Subscription.objects.filter(
        status='trialing',
        trial_end__lte=timezone.now(),
    ).select_related('plan', 'organization')

    free_plan = Plan.objects.filter(
        plan_type='free', interval='month', is_active=True
    ).first()

    count = 0
    for sub in expired_trials:
        if sub.plan.plan_type == 'free' or not sub.stripe_subscription_id:
            # No payment method / no Stripe - downgrade to free
            if free_plan:
                sub.plan = free_plan
                sub.status = 'expired'
                sub.save(update_fields=['plan', 'status'])

                org = sub.organization
                org.plan = 'free'
                org.max_contacts = free_plan.max_contacts
                org.max_emails_per_month = free_plan.max_emails_per_month
                org.save(update_fields=['plan', 'max_contacts', 'max_emails_per_month'])
        else:
            # Has Stripe subscription - let Stripe handle the transition
            sub.status = 'active'
            sub.save(update_fields=['status'])

        BillingEvent.objects.create(
            organization=sub.organization,
            event_type='trial_expired',
            description=f"Trial period expired for {sub.plan.name}",
        )
        count += 1

    if count:
        logger.info(f"Processed {count} expired trials")
    return count


@shared_task
def reset_monthly_email_usage():
    """Reset monthly email usage counters."""
    from .models import Subscription

    today = timezone.now().date()
    subscriptions = Subscription.objects.filter(
        status__in=['active', 'trialing'],
        usage_reset_date__lt=today - timedelta(days=28),
    )

    count = subscriptions.update(
        emails_sent_this_month=0,
        usage_reset_date=today,
    )

    if count:
        logger.info(f"Reset email usage for {count} subscriptions")
    return count


@shared_task
def send_trial_ending_reminders():
    """Send reminders to organizations whose trial is ending in 3 days."""
    from .models import Subscription, BillingEvent

    three_days_from_now = timezone.now() + timedelta(days=3)
    ending_soon = Subscription.objects.filter(
        status='trialing',
        trial_end__date=three_days_from_now.date(),
    ).select_related('organization')

    count = 0
    for sub in ending_soon:
        # Check if we already sent a reminder
        already_sent = BillingEvent.objects.filter(
            organization=sub.organization,
            event_type='trial_ending',
            created_at__date=timezone.now().date(),
        ).exists()

        if not already_sent:
            BillingEvent.objects.create(
                organization=sub.organization,
                event_type='trial_ending',
                description="Trial ending in 3 days",
            )
            count += 1

    if count:
        logger.info(f"Sent {count} trial ending reminders")
    return count
