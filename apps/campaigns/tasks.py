"""
Celery tasks for the Email Campaigns app.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


def _mark_sent(recipient, msg):
    """
    Record a successful send on a recipient.

    Captures the provider's per-recipient ids when the backend supplies them.
    Postal does not echo custom headers, so postal_id/postal_token are the only
    link a later delivery or bounce webhook has back to this row.
    """
    recipient.status = 'sent'
    recipient.sent_at = timezone.now()
    update_fields = ['status', 'sent_at', 'updated_at']

    postal_status = getattr(msg, 'postal_status', None)
    if postal_status:
        recipient.postal_id = postal_status.get('postal_id')
        recipient.postal_token = postal_status.get('token') or ''
        update_fields += ['postal_id', 'postal_token']

    recipient.save(update_fields=update_fields)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_campaign_emails(self, campaign_id: str):
    """
    Coordinator task: dispatch batches for all pending recipients.
    Called immediately after a campaign is set to 'sending' status.
    """
    from .models import Campaign, CampaignRecipient

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
        return

    if campaign.status != 'sending':
        logger.warning(
            f"Campaign {campaign_id} is not in 'sending' status (current: {campaign.status})"
        )
        return

    pending_ids = list(
        CampaignRecipient.objects.filter(
            campaign=campaign, status='pending'
        ).values_list('id', flat=True)
    )

    if not pending_ids:
        logger.info(f"Campaign {campaign_id}: no pending recipients, marking as sent")
        campaign.status = 'sent'
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=['status', 'completed_at', 'updated_at'])
        return

    # Chunk into batches and dispatch with stagger
    chunks = [pending_ids[i:i + BATCH_SIZE] for i in range(0, len(pending_ids), BATCH_SIZE)]
    for index, chunk in enumerate(chunks):
        chunk_strs = [str(pk) for pk in chunk]
        send_campaign_email_batch.apply_async(
            args=[campaign_id, chunk_strs],
            countdown=index * 5,  # 5s stagger per batch to avoid SES burst limits
        )

    logger.info(
        f"Campaign {campaign_id}: dispatched {len(chunks)} batch(es) "
        f"for {len(pending_ids)} recipients"
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_campaign_email_batch(self, campaign_id: str, recipient_ids: list):
    """
    Send one email per recipient in this batch.
    Updates recipient status and checks if campaign is fully sent.
    """
    from django.core.mail import EmailMessage
    from .models import Campaign, CampaignRecipient
    from .services import EmailTrackingService
    from apps.email_config.services import EmailConfigService

    try:
        campaign = Campaign.objects.select_related('template', 'organization').get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found in batch task")
        return

    # Check sending limits before processing batch
    allowed, reason = EmailConfigService.check_sending_limits(campaign.organization)
    if not allowed:
        logger.warning(f"Campaign {campaign_id} batch blocked: {reason}")
        return

    recipients = CampaignRecipient.objects.select_related('contact').filter(
        id__in=recipient_ids, status='pending'
    )

    # Resolve org-specific from address — campaign sender overrides config defaults
    if campaign.sender_name and campaign.sender_email:
        from_email = f"{campaign.sender_name} <{campaign.sender_email}>"
    else:
        cfg_name, cfg_email = EmailConfigService.get_default_from(campaign.organization)
        from_email = f"{cfg_name} <{cfg_email}>"

    # Get org-specific email backend connection (reused for all recipients in batch)
    connection = EmailConfigService.get_connection(campaign.organization)

    for recipient in recipients:
        try:
            html_body = EmailTrackingService.render_html_for_recipient(campaign, recipient)
            unsubscribe_url = EmailTrackingService.get_unsubscribe_url(recipient)

            msg = EmailMessage(
                subject=campaign.subject or '(No subject)',
                body=html_body,
                from_email=from_email,
                to=[recipient.email],
                reply_to=[campaign.reply_to_email] if campaign.reply_to_email else None,
                headers={
                    'List-Unsubscribe': f'<{unsubscribe_url}>',
                    'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                    'X-Campaign-ID': str(campaign.id),
                    'X-Recipient-ID': str(recipient.id),
                },
                connection=connection,
            )
            msg.content_subtype = 'html'

            # Attach anymail metadata for webhook correlation (if anymail is installed)
            try:
                msg.esp_extra = {'metadata': {'recipient_id': str(recipient.id)}}
            except Exception:
                pass

            msg.send(fail_silently=False)
            _mark_sent(recipient, msg)
            logger.info(f"Email sent to {recipient.email} for campaign {campaign_id}")

        except Exception as exc:
            logger.error(
                f"Failed to send email to {recipient.email} for campaign {campaign_id}: {exc}"
            )
            recipient.status = 'failed'
            recipient.save(update_fields=['status', 'updated_at'])

    # Check if all recipients are processed; if so, mark campaign as sent
    pending_remaining = CampaignRecipient.objects.filter(
        campaign=campaign, status='pending'
    ).count()

    if pending_remaining == 0:
        campaign.status = 'sent'
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=['status', 'completed_at', 'updated_at'])
        logger.info(f"Campaign {campaign_id} fully sent")
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_org_admins(
                organization=campaign.organization,
                notification_type='campaign_sent',
                title='Campaign sent',
                message=f'"{campaign.name}" finished sending to {campaign.recipient_count:,} recipients.',
                data={'campaign_id': str(campaign.id)},
            )
        except Exception:
            pass


@shared_task
def process_scheduled_campaigns():
    """
    Beat task (every 60s): find campaigns with status='scheduled'
    and scheduled_at <= now. Trigger sending.
    """
    from .models import Campaign
    from .services import CampaignService

    now = timezone.now()
    due_campaigns = Campaign.objects.filter(
        status='scheduled',
        scheduled_at__lte=now,
    )

    for campaign in due_campaigns:
        try:
            campaign.status = 'sending'
            campaign.sent_at = now
            campaign.save(update_fields=['status', 'sent_at', 'updated_at'])

            try:
                ab_test = campaign.ab_test
                has_ab = ab_test.status == 'draft'
            except Exception:
                has_ab = False

            if has_ab:
                from .services import ABTestService
                ABTestService.prepare_ab_recipients(campaign, ab_test)
                ab_test.status = 'testing'
                ab_test.save(update_fields=['status', 'updated_at'])
                send_ab_variant_emails.delay(str(campaign.id), 'a')
                send_ab_variant_emails.delay(str(campaign.id), 'b')
                if ab_test.winner_selection == 'auto':
                    check_ab_winner.apply_async(
                        args=[str(ab_test.id)],
                        countdown=ab_test.test_duration_hours * 3600,
                    )
                else:
                    notify_ab_manual_winner_needed.apply_async(
                        args=[str(ab_test.id)],
                        countdown=ab_test.test_duration_hours * 3600,
                    )
            else:
                CampaignService.prepare_recipients(campaign)
                send_campaign_emails.delay(str(campaign.id))

            logger.info(f"Scheduled campaign {campaign.id} triggered for sending")
        except Exception as exc:
            logger.error(f"Failed to trigger scheduled campaign {campaign.id}: {exc}")


@shared_task
def check_stuck_campaigns():
    """
    Beat task (every 30min): find campaigns stuck in 'sending'
    (sent_at > 30min ago) that still have pending recipients.
    Re-queue send_campaign_emails for them.
    """
    from datetime import timedelta
    from .models import Campaign, CampaignRecipient

    cutoff = timezone.now() - timedelta(minutes=30)
    stuck_ids = (
        CampaignRecipient.objects.filter(status='pending')
        .values_list('campaign_id', flat=True)
        .distinct()
    )
    # Exclude campaigns that are intentionally waiting for an A/B test winner
    stuck_campaigns = Campaign.objects.filter(
        id__in=stuck_ids,
        status='sending',
        sent_at__lt=cutoff,
    ).exclude(ab_test__status__in=['testing', 'winner_declared'])

    for campaign in stuck_campaigns:
        logger.warning(f"Re-queueing stuck campaign {campaign.id}")
        send_campaign_emails.delay(str(campaign.id))


# ── A/B test tasks ──────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_ab_variant_emails(self, campaign_id: str, variant: str):
    """Dispatch batch tasks for one A/B variant."""
    from .models import Campaign, CampaignRecipient

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.error(f"AB send: Campaign {campaign_id} not found")
        return

    pending_ids = list(
        CampaignRecipient.objects.filter(
            campaign=campaign, ab_variant=variant, status='pending'
        ).values_list('id', flat=True)
    )
    if not pending_ids:
        return

    chunks = [pending_ids[i:i + BATCH_SIZE] for i in range(0, len(pending_ids), BATCH_SIZE)]
    for idx, chunk in enumerate(chunks):
        send_ab_variant_batch.apply_async(
            args=[campaign_id, [str(pk) for pk in chunk], variant],
            countdown=idx * 5,
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_ab_variant_batch(self, campaign_id: str, recipient_ids: list, variant: str):
    """Send one email per recipient for an A/B variant batch."""
    from django.core.mail import EmailMessage
    from apps.email_config.services import EmailConfigService
    from .models import Campaign, CampaignRecipient
    from .services import ABTestService, EmailTrackingService

    try:
        campaign = Campaign.objects.select_related('template', 'ab_test').get(id=campaign_id)
    except Campaign.DoesNotExist:
        return

    ab_test = campaign.ab_test
    config = ABTestService.get_variant_config(campaign, ab_test, variant)

    # The same rate-limit gate the non-A/B path applies. Without it an A/B
    # campaign could send straight past the organization's limits and past a
    # guardrail pause.
    allowed, reason = EmailConfigService.check_sending_limits(campaign.organization)
    if not allowed:
        logger.warning(f"AB batch for campaign {campaign_id} blocked: {reason}")
        return

    # Fall back to the organization's configured sender rather than None: a
    # message with no From address is rejected outright by the Postal API.
    sender = config['sender_name']
    if sender and campaign.sender_email:
        from_email = f"{sender} <{campaign.sender_email}>"
    else:
        cfg_name, cfg_email = EmailConfigService.get_default_from(campaign.organization)
        from_email = f"{sender or cfg_name} <{cfg_email}>"

    # Use the organization's own backend. Previously this fell through to the
    # global EMAIL_BACKEND, so A/B mail went out through the platform's
    # provider while every other campaign used the organization's.
    connection = EmailConfigService.get_connection(campaign.organization)

    recipients = CampaignRecipient.objects.select_related('contact').filter(
        id__in=recipient_ids, ab_variant=variant, status='pending'
    )
    for recipient in recipients:
        try:
            html_body = EmailTrackingService.render_html_for_recipient(
                campaign, recipient, template_override=config['template']
            )
            unsubscribe_url = EmailTrackingService.get_unsubscribe_url(recipient)
            msg = EmailMessage(
                subject=config['subject'] or '(No subject)',
                body=html_body,
                from_email=from_email,
                to=[recipient.email],
                reply_to=[campaign.reply_to_email] if campaign.reply_to_email else None,
                headers={
                    'List-Unsubscribe': f'<{unsubscribe_url}>',
                    'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                    'X-Campaign-ID': str(campaign.id),
                    'X-Recipient-ID': str(recipient.id),
                    'X-AB-Variant': variant.upper(),
                },
                connection=connection,
            )
            msg.content_subtype = 'html'
            msg.esp_extra = {'metadata': {'recipient_id': str(recipient.id)}}
            msg.send(fail_silently=False)
            _mark_sent(recipient, msg)
        except Exception as exc:
            logger.error(f"AB batch: failed {recipient.email}: {exc}")
            recipient.status = 'failed'
            recipient.save(update_fields=['status', 'updated_at'])

    ABTestService.compute_variant_stats(ab_test)


@shared_task
def check_ab_winner(ab_test_id: str):
    """Auto-select the A/B winner and trigger sending to remainder."""
    from .models import ABTest
    from .services import ABTestService

    try:
        ab_test = ABTest.objects.select_related('campaign').get(id=ab_test_id)
    except ABTest.DoesNotExist:
        return

    if ab_test.status != 'testing':
        return  # already resolved (possibly manually)

    winner = ABTestService.determine_winner(ab_test)
    if not winner:
        return

    ab_test.winner_variant = winner
    ab_test.status = 'winner_declared'
    ab_test.save(update_fields=['winner_variant', 'status', 'updated_at'])
    logger.info(f"AB winner auto-selected: {winner.upper()} for test {ab_test_id}")

    send_ab_winner_to_remainder.delay(str(ab_test_id))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_ab_winner_to_remainder(self, ab_test_id: str):
    """Send the winning variant to all remaining 'winner' recipients."""
    from django.core.mail import EmailMessage
    from .models import ABTest, CampaignRecipient
    from .services import ABTestService, EmailTrackingService

    try:
        ab_test = ABTest.objects.select_related('campaign__template').get(id=ab_test_id)
    except ABTest.DoesNotExist:
        return

    if not ab_test.winner_variant:
        return

    campaign = ab_test.campaign
    config = ABTestService.get_variant_config(campaign, ab_test, ab_test.winner_variant)
    sender = config['sender_name']
    from_email = f"{sender} <{campaign.sender_email}>" if sender and campaign.sender_email else None

    pending_ids = list(
        CampaignRecipient.objects.filter(
            campaign=campaign, ab_variant='winner', status='pending'
        ).values_list('id', flat=True)
    )
    if not pending_ids:
        _finalize_ab_campaign(campaign, ab_test)
        return

    chunks = [pending_ids[i:i + BATCH_SIZE] for i in range(0, len(pending_ids), BATCH_SIZE)]
    for idx, chunk in enumerate(chunks):
        send_ab_winner_batch.apply_async(
            args=[str(ab_test_id), [str(pk) for pk in chunk]],
            countdown=idx * 5,
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_ab_winner_batch(self, ab_test_id: str, recipient_ids: list):
    """Send winner emails to one batch of remainder recipients."""
    from django.core.mail import EmailMessage
    from apps.email_config.services import EmailConfigService
    from .models import ABTest, CampaignRecipient
    from .services import ABTestService, EmailTrackingService

    try:
        ab_test = ABTest.objects.select_related('campaign__template').get(id=ab_test_id)
    except ABTest.DoesNotExist:
        return

    campaign = ab_test.campaign
    config = ABTestService.get_variant_config(campaign, ab_test, ab_test.winner_variant)

    allowed, reason = EmailConfigService.check_sending_limits(campaign.organization)
    if not allowed:
        logger.warning(f"AB winner batch for campaign {campaign.id} blocked: {reason}")
        return

    sender = config['sender_name']
    if sender and campaign.sender_email:
        from_email = f"{sender} <{campaign.sender_email}>"
    else:
        cfg_name, cfg_email = EmailConfigService.get_default_from(campaign.organization)
        from_email = f"{sender or cfg_name} <{cfg_email}>"

    # As in send_ab_variant_batch: use the organization's own backend rather
    # than falling through to the global EMAIL_BACKEND.
    connection = EmailConfigService.get_connection(campaign.organization)

    recipients = CampaignRecipient.objects.select_related('contact').filter(
        id__in=recipient_ids, ab_variant='winner', status='pending'
    )
    for recipient in recipients:
        try:
            html_body = EmailTrackingService.render_html_for_recipient(
                campaign, recipient, template_override=config['template']
            )
            unsubscribe_url = EmailTrackingService.get_unsubscribe_url(recipient)
            msg = EmailMessage(
                subject=config['subject'] or '(No subject)',
                body=html_body,
                from_email=from_email,
                to=[recipient.email],
                reply_to=[campaign.reply_to_email] if campaign.reply_to_email else None,
                headers={
                    'List-Unsubscribe': f'<{unsubscribe_url}>',
                    'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                    'X-Campaign-ID': str(campaign.id),
                    'X-Recipient-ID': str(recipient.id),
                    'X-AB-Variant': f"Winner ({ab_test.winner_variant.upper()})",
                },
                connection=connection,
            )
            msg.content_subtype = 'html'
            msg.esp_extra = {'metadata': {'recipient_id': str(recipient.id)}}
            msg.send(fail_silently=False)
            _mark_sent(recipient, msg)
        except Exception as exc:
            logger.error(f"AB winner batch: failed {recipient.email}: {exc}")
            recipient.status = 'failed'
            recipient.save(update_fields=['status', 'updated_at'])

    pending_remaining = CampaignRecipient.objects.filter(
        campaign=campaign, ab_variant='winner', status='pending'
    ).count()
    if pending_remaining == 0:
        _finalize_ab_campaign(campaign, ab_test)


def _finalize_ab_campaign(campaign, ab_test):
    """Mark campaign as sent and AB test as completed once all sending is done."""
    from .models import CampaignRecipient
    from .services import ABTestService

    if CampaignRecipient.objects.filter(campaign=campaign, status='pending').exists():
        return

    ABTestService.compute_variant_stats(ab_test)
    ab_test.status = 'completed'
    ab_test.winner_sent_at = timezone.now()
    ab_test.save(update_fields=['status', 'winner_sent_at', 'updated_at'])

    campaign.status = 'sent'
    campaign.completed_at = timezone.now()
    campaign.save(update_fields=['status', 'completed_at', 'updated_at'])
    logger.info(f"AB campaign {campaign.id} completed")
    try:
        from apps.notifications.services import NotificationService
        winner = ab_test.winner_variant.upper() if ab_test.winner_variant else '?'
        NotificationService.notify_org_admins(
            organization=campaign.organization,
            notification_type='ab_test_completed',
            title='A/B test completed',
            message=f'"{campaign.name}" A/B test finished. Variant {winner} won.',
            data={'campaign_id': str(campaign.id), 'ab_test_id': str(ab_test.id)},
        )
    except Exception:
        pass


@shared_task
def notify_ab_manual_winner_needed(ab_test_id: str):
    """Fire after test duration for manual-selection A/B tests to prompt the user."""
    from .models import ABTest
    try:
        ab_test = ABTest.objects.select_related('campaign__organization').get(id=ab_test_id)
    except ABTest.DoesNotExist:
        return

    if ab_test.status != 'testing' or ab_test.winner_selection != 'manual':
        return

    from apps.notifications.services import NotificationService
    campaign = ab_test.campaign
    NotificationService.notify_org_admins(
        organization=campaign.organization,
        notification_type='ab_test_winner_needed',
        title='A/B test ready — pick a winner',
        message=(
            f'"{campaign.name}" A/B test has ended. '
            f'Review the results and declare a winner.'
        ),
        data={'campaign_id': str(campaign.id), 'ab_test_id': str(ab_test_id)},
    )
