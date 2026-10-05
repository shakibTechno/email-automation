"""
Services for the Email Campaigns app.
"""
import logging
import re
from django.core.mail import send_mail
from django.conf import settings
from apps.contacts.models import Contact, ContactTag

logger = logging.getLogger(__name__)


class CampaignService:
    """Service class for campaign operations."""

    @staticmethod
    def calculate_recipients(campaign):
        """Return a queryset of Contact objects based on campaign's recipient settings."""
        base_qs = Contact.objects.filter(
            organization=campaign.organization,
            is_subscribed=True,
            bounced_at__isnull=True,
        )

        if campaign.recipient_type == 'by_tags' and campaign.recipient_tags.exists():
            tag_ids = campaign.recipient_tags.values_list('id', flat=True)
            contact_ids = ContactTag.objects.filter(
                tag_id__in=tag_ids
            ).values_list('contact_id', flat=True).distinct()
            base_qs = base_qs.filter(id__in=contact_ids)

        return base_qs

    @staticmethod
    def get_recipient_count(campaign):
        """Return the count of recipients for a campaign."""
        return CampaignService.calculate_recipients(campaign).count()

    @staticmethod
    def prepare_recipients(campaign):
        """Create CampaignRecipient records from the calculated contacts."""
        from .models import CampaignRecipient

        contacts = CampaignService.calculate_recipients(campaign)
        recipients = []
        for contact in contacts.iterator():
            recipients.append(CampaignRecipient(
                campaign=campaign,
                contact=contact,
                email=contact.email,
                status='pending',
            ))

        CampaignRecipient.objects.bulk_create(recipients, ignore_conflicts=True)
        campaign.recipient_count = len(recipients)
        campaign.save(update_fields=['recipient_count'])
        return len(recipients)

    @staticmethod
    def render_html(campaign, contact=None, template_override=None):
        """Render campaign template HTML with merge tags replaced."""
        template = template_override or campaign.template
        if not template:
            return ''

        html = template.html_content or ''

        # Sample merge data
        if contact:
            merge_data = {
                'first_name': contact.first_name or '',
                'last_name': contact.last_name or '',
                'email': contact.email,
                'company': contact.company or '',
            }
        else:
            merge_data = {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'company': 'Acme Inc.',
            }

        merge_data['unsubscribe_url'] = '#unsubscribe'

        # Replace {{tag}} merge tags
        for key, value in merge_data.items():
            html = re.sub(
                r'\{\{\s*' + re.escape(key) + r'\s*\}\}',
                value,
                html
            )

        return html

    @staticmethod
    def send_test_email(campaign, test_emails):
        """Send a test email to the specified addresses."""
        html_content = CampaignService.render_html(campaign)
        subject = campaign.subject or '(No subject)'
        from_email = (
            f"{campaign.sender_name} <{campaign.sender_email}>"
            if campaign.sender_name and campaign.sender_email
            else settings.DEFAULT_FROM_EMAIL
        )

        for email in test_emails:
            try:
                send_mail(
                    subject=f"[TEST] {subject}",
                    message='',
                    from_email=from_email,
                    recipient_list=[email],
                    html_message=html_content,
                    fail_silently=False,
                )
                logger.info(f"Test email sent to {email} for campaign {campaign.id}")
            except Exception as e:
                logger.error(f"Failed to send test email to {email}: {e}")
                raise

        return len(test_emails)


class EmailTrackingService:
    """Per-recipient HTML rendering with tracking links, pixel, and unsubscribe URL."""

    @staticmethod
    def generate_unsubscribe_token(recipient):
        from django.core import signing
        return signing.dumps(str(recipient.id), salt='unsubscribe')

    @staticmethod
    def get_unsubscribe_url(recipient):
        from django.conf import settings
        token = EmailTrackingService.generate_unsubscribe_token(recipient)
        base = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        return f"{base}/unsubscribe/{token}/"

    @staticmethod
    def get_open_pixel_url(recipient):
        from django.conf import settings
        base = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        return f"{base}/track/o/{recipient.tracking_id}/"

    @staticmethod
    def get_click_tracking_url(link, recipient):
        from django.conf import settings
        base = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        return f"{base}/track/c/{link.id}/{recipient.tracking_id}/"

    @staticmethod
    def wrap_links(html, campaign, recipient):
        """Replace all href URLs with click-tracked URLs."""
        from .models import CampaignLink
        position = [0]

        def replace_href(match):
            url = match.group(1)
            if url.startswith(('mailto:', 'tel:', '#', 'javascript:')):
                return match.group(0)
            link, _ = CampaignLink.objects.get_or_create(
                campaign=campaign,
                original_url=url,
                defaults={'position': position[0]},
            )
            position[0] += 1
            tracked_url = EmailTrackingService.get_click_tracking_url(link, recipient)
            return f'href="{tracked_url}"'

        return re.sub(r'href="([^"]+)"', replace_href, html)

    @staticmethod
    def inject_tracking_pixel(html, recipient):
        """Inject 1×1 tracking pixel before </body>."""
        pixel_url = EmailTrackingService.get_open_pixel_url(recipient)
        pixel = (
            f'<img src="{pixel_url}" width="1" height="1" '
            f'style="display:none;border:0;" alt="">'
        )
        if '</body>' in html:
            return html.replace('</body>', f'{pixel}</body>', 1)
        return html + pixel

    @staticmethod
    def render_html_for_recipient(campaign, recipient, template_override=None):
        """Full per-recipient render: merge tags + link tracking + pixel."""
        html = CampaignService.render_html(campaign, recipient.contact, template_override=template_override)
        unsubscribe_url = EmailTrackingService.get_unsubscribe_url(recipient)
        html = html.replace('#unsubscribe', unsubscribe_url)
        html = EmailTrackingService.wrap_links(html, campaign, recipient)
        html = EmailTrackingService.inject_tracking_pixel(html, recipient)
        return html


class ABTestService:
    """Service for A/B test operations."""

    @staticmethod
    def get_variant_config(campaign, ab_test, variant_letter):
        """Return effective subject, sender_name, template for the given variant."""
        from .models import ABTestVariant
        try:
            v = ab_test.variants.get(variant=variant_letter)
        except ABTestVariant.DoesNotExist:
            return {
                'subject': campaign.subject,
                'sender_name': campaign.sender_name,
                'template': campaign.template,
            }
        return {
            'subject': v.subject if ab_test.test_type == 'subject' and v.subject else campaign.subject,
            'sender_name': v.sender_name if ab_test.test_type == 'sender_name' and v.sender_name else campaign.sender_name,
            'template': v.template if ab_test.test_type == 'content' and v.template else campaign.template,
        }

    @staticmethod
    def prepare_ab_recipients(campaign, ab_test):
        """Split contacts into variant A, variant B, and winner groups."""
        import random
        from .models import CampaignRecipient, ABTestVariant

        contacts = list(CampaignService.calculate_recipients(campaign).iterator())
        random.shuffle(contacts)

        total = len(contacts)
        half_test = int(total * ab_test.test_percentage / 100 / 2)

        variant_a_contacts = contacts[:half_test]
        variant_b_contacts = contacts[half_test: half_test * 2]
        winner_contacts = contacts[half_test * 2:]

        recipients = []
        for contact in variant_a_contacts:
            recipients.append(CampaignRecipient(campaign=campaign, contact=contact, email=contact.email, ab_variant='a'))
        for contact in variant_b_contacts:
            recipients.append(CampaignRecipient(campaign=campaign, contact=contact, email=contact.email, ab_variant='b'))
        for contact in winner_contacts:
            recipients.append(CampaignRecipient(campaign=campaign, contact=contact, email=contact.email, ab_variant='winner'))

        CampaignRecipient.objects.bulk_create(recipients, ignore_conflicts=True)

        # Update recipient counts on variants
        ABTestVariant.objects.filter(ab_test=ab_test, variant='a').update(recipient_count=len(variant_a_contacts))
        ABTestVariant.objects.filter(ab_test=ab_test, variant='b').update(recipient_count=len(variant_b_contacts))

        campaign.recipient_count = total
        campaign.save(update_fields=['recipient_count'])
        return total

    @staticmethod
    def compute_variant_stats(ab_test):
        """Refresh open/click/sent counts on each variant from CampaignRecipient data."""
        from .models import CampaignRecipient, ABTestVariant
        from django.db.models import Count, Q

        for letter in ('a', 'b'):
            qs = CampaignRecipient.objects.filter(campaign=ab_test.campaign, ab_variant=letter)
            sent = qs.exclude(status='pending').count()
            opens = qs.filter(opened_at__isnull=False).count()
            clicks = qs.filter(clicked_at__isnull=False).count()
            ABTestVariant.objects.filter(ab_test=ab_test, variant=letter).update(
                sent_count=sent, open_count=opens, click_count=clicks
            )

    @staticmethod
    def determine_winner(ab_test):
        """Pick winner variant based on winner_criteria."""
        ABTestService.compute_variant_stats(ab_test)
        from .models import ABTestVariant
        try:
            va = ab_test.variants.get(variant='a')
            vb = ab_test.variants.get(variant='b')
        except ABTestVariant.DoesNotExist:
            return None

        if ab_test.winner_criteria == 'open_rate':
            score_a, score_b = va.open_rate, vb.open_rate
        else:
            score_a, score_b = va.click_rate, vb.click_rate

        return 'a' if score_a >= score_b else 'b'
