from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campaigns'
    verbose_name = 'Email Campaigns'

    def ready(self):
        """Connect Anymail signal handlers for delivery event tracking."""
        try:
            from anymail.signals import tracking
            from django.dispatch import receiver

            @receiver(tracking)
            def handle_anymail_tracking(sender, event, esp_name, **kwargs):
                """Update CampaignRecipient status from ESP delivery events."""
                import logging
                from django.utils import timezone
                logger = logging.getLogger(__name__)

                recipient_id = (event.metadata or {}).get('recipient_id')
                if not recipient_id:
                    return

                from .models import CampaignRecipient
                try:
                    recipient = CampaignRecipient.objects.get(id=recipient_id)
                except CampaignRecipient.DoesNotExist:
                    return

                event_type = event.event_type
                now = timezone.now()

                if event_type == 'delivered':
                    recipient.status = 'delivered'
                    recipient.save(update_fields=['status', 'updated_at'])
                elif event_type == 'bounced':
                    recipient.status = 'bounced'
                    recipient.bounced_at = now
                    recipient.save(update_fields=['status', 'bounced_at', 'updated_at'])
                    # Mark the contact as bounced
                    recipient.contact.mark_bounced()
                elif event_type == 'complained':
                    recipient.status = 'complained'
                    recipient.complained_at = now
                    recipient.save(update_fields=['status', 'complained_at', 'updated_at'])

                logger.info(
                    f"Anymail event '{event_type}' processed for recipient {recipient_id}"
                )

        except ImportError:
            # anymail not installed — skip signal registration
            pass
