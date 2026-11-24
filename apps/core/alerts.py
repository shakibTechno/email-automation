"""
What is wrong right now.

The dashboard's first row. Each check reads state the product already keeps --
a guardrail that tripped, a domain that never verified, a quota running out --
and turns it into one line with somewhere to go.

Two rules:

- **Nothing to say means nothing shown.** The card is absent when the list is
  empty, never a green panel. A panel that is always there is one people stop
  reading, and then it cannot warn them.
- **Each check is gated by the permission its data belongs to.** This list
  spans email settings, billing, campaigns and automation, so without that a
  viewer would learn the organization's billing state from its dashboard.
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.core import access

ACTION = 'action'
SOON = 'soon'

# Past this share of the monthly allowance, the end of the month is a risk
# worth naming while there is still time to act on it.
QUOTA_WARN_AT = 0.8
# A campaign that has been mid-send this long has stopped, whatever its status
# column says.
STUCK_SENDING_HOURS = 6
TRIAL_WARN_DAYS = 7


def _sending_paused(organization):
    from apps.email_config.models import EmailConfiguration

    config = EmailConfiguration.objects.filter(organization=organization).first()
    if not config or not config.sending_paused_due_to_threshold:
        return None

    # strftime has no portable "day without a leading zero": %-d is glibc only
    # and raises on Windows, which is where this first blew up.
    when = config.sending_paused_at
    day = when.strftime('%d %b').lstrip('0') if when else ''
    return {
        'id': 'sending-paused',
        'level': ACTION,
        'title': 'Sending is paused',
        'detail': (
            'A bounce or complaint guardrail stopped sending'
            + (f' on {day}' if day else '')
            + '. Nothing goes out until it is resumed.'
        ),
        'action': 'Review and resume',
        'url': '/settings?tab=email',
    }


def _domain_unverified(organization):
    from apps.email_config.models import SendingDomain

    pending = SendingDomain.objects.filter(organization=organization).exclude(
        status=SendingDomain.STATUS_VERIFIED
    ).first()
    if pending is None:
        return None

    return {
        'id': f'domain-{pending.pk}',
        'level': ACTION,
        'title': 'Domain not verified',
        'detail': (
            f'{pending.domain} is not verified yet, so mail still sends from '
            'the shared address.'
        ),
        'action': 'Check DNS',
        'url': '/settings?tab=email',
    }


def _quota(organization):
    from apps.billing.models import Subscription

    subscription = (
        Subscription.objects.filter(organization=organization)
        .select_related('plan')
        .first()
    )
    if subscription is None or not subscription.plan_id:
        return None

    limit = subscription.plan.max_emails_per_month or 0
    used = subscription.emails_sent_this_month or 0
    if limit <= 0 or used < limit * QUOTA_WARN_AT:
        return None

    exhausted = used >= limit
    return {
        'id': 'quota',
        'level': ACTION if exhausted else SOON,
        'title': 'Monthly email quota used up' if exhausted else 'Email quota running out',
        'detail': f'{used:,} of {limit:,} emails this month.',
        'action': 'See plans',
        'url': '/billing',
    }


def _trial_ending(organization):
    from apps.billing.models import Subscription

    subscription = Subscription.objects.filter(organization=organization).first()
    if subscription is None or not subscription.is_trialing or not subscription.trial_end:
        return None

    days = (subscription.trial_end - timezone.now()).days
    if days > TRIAL_WARN_DAYS:
        return None

    return {
        'id': 'trial',
        'level': SOON if days > 2 else ACTION,
        'title': 'Trial is ending',
        'detail': (
            'Your trial ends today.' if days <= 0
            else f'Your trial ends in {days} day{"" if days == 1 else "s"}.'
        ),
        'action': 'Choose a plan',
        'url': '/billing',
    }


def _stuck_campaign(organization):
    from apps.campaigns.models import Campaign

    cutoff = timezone.now() - timedelta(hours=STUCK_SENDING_HOURS)
    stuck = Campaign.objects.filter(
        organization=organization, status='sending', updated_at__lt=cutoff
    ).first()
    if stuck is None:
        return None

    return {
        'id': f'campaign-{stuck.pk}',
        'level': ACTION,
        'title': 'Campaign stuck mid-send',
        'detail': (
            f'“{stuck.name}” has been sending for more than '
            f'{STUCK_SENDING_HOURS} hours.'
        ),
        'action': 'Open campaign',
        'url': f'/campaigns/{stuck.pk}',
    }


def _workflow_failures(organization):
    from apps.workflows.models import WorkflowExecution

    since = timezone.now() - timedelta(days=7)
    failed = WorkflowExecution.objects.filter(
        workflow__organization=organization, status='failed', updated_at__gte=since
    ).count()
    if not failed:
        return None

    return {
        'id': 'workflow-failures',
        'level': SOON,
        'title': 'Workflow runs failed',
        'detail': f'{failed} execution{"" if failed == 1 else "s"} failed in the last 7 days.',
        'action': 'Open workflows',
        'url': '/workflows',
    }


def _sequence_failures(organization):
    from apps.sequences.models import SequenceStepExecution

    since = timezone.now() - timedelta(days=7)
    failed = SequenceStepExecution.objects.filter(
        enrollment__sequence__organization=organization,
        status='failed',
        updated_at__gte=since,
    ).count()
    if not failed:
        return None

    return {
        'id': 'sequence-failures',
        'level': SOON,
        'title': 'Sequence emails failed',
        'detail': f'{failed} step{"" if failed == 1 else "s"} failed to send in the last 7 days.',
        'action': 'Open sequences',
        'url': '/sequences',
    }


# The permission each check's data belongs to. A role without it is not told
# the alert exists -- the same rule the calendar follows for its sources.
CHECKS = (
    ('email_config.view', _sending_paused),
    ('email_config.view', _domain_unverified),
    ('billing.view', _quota),
    ('billing.view', _trial_ending),
    ('campaigns.view', _stuck_campaign),
    ('workflows.view', _workflow_failures),
    ('sequences.view', _sequence_failures),
)

# ACTION before SOON; within a level, the order declared above.
_LEVEL_ORDER = {ACTION: 0, SOON: 1}


def alerts_for(user):
    """Everything wrong that this user is allowed to know about."""
    organization = getattr(user, 'organization', None)
    if organization is None:
        return []

    found = []
    for permission, check in CHECKS:
        if not access.has_permission(user, permission):
            continue
        alert = check(organization)
        if alert is not None:
            found.append(alert)

    found.sort(key=lambda a: _LEVEL_ORDER.get(a['level'], 9))
    return found
