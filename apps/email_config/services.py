"""
Services for per-organization email configuration.
"""
import logging
from django.utils import timezone
from django.core.mail import get_connection, EmailMessage
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


class EmailConfigService:
    """Resolve, test, and manage per-org email sending configuration."""

    @staticmethod
    def get_or_create(organization):
        """Return the EmailConfiguration for this org, creating defaults if needed."""
        from .models import EmailConfiguration
        config, _ = EmailConfiguration.objects.get_or_create(organization=organization)
        return config

    @staticmethod
    def get_postal_connection(organization):
        """
        Return a Postal backend for this organization, or None.

        None means Postal cannot be used right now — it is not enabled, the
        organization has no tenant, or the tenant has no sending-enabled domain.
        Postal rejects any From address whose domain it has not verified
        (UnauthenticatedFromAddress), so sending anyway would fail hard rather
        than degrade. The caller falls back to SMTP.
        """
        if not django_settings.POSTAL_ENABLED or not django_settings.POSTAL_URL:
            return None

        from .backends import PostalEmailBackend
        from .provisioning import PostalProvisioningService

        tenant = PostalProvisioningService.get_tenant(organization)
        if not tenant or not tenant.can_send:
            return None

        return PostalEmailBackend(api_key=tenant.api_key, fail_silently=False)

    @staticmethod
    def get_connection(organization):
        """
        Return an open Django email backend connection for this organization.

        Resolution order:
          * 'postal'           — the platform mail server, explicitly chosen
          * 'platform_default' — Postal when the org has a usable tenant,
                                 otherwise the platform's shared SMTP
          * everything else    — the organization's own provider credentials
        """
        from .models import EmailConfiguration

        try:
            config = EmailConfiguration.objects.get(organization=organization)
        except EmailConfiguration.DoesNotExist:
            return (
                EmailConfigService.get_postal_connection(organization)
                or get_connection()
            )

        provider = config.provider

        if provider == 'postal':
            postal = EmailConfigService.get_postal_connection(organization)
            if postal:
                return postal
            # Explicitly configured for Postal but not usable yet. Fall through
            # to the platform default so transactional mail still goes out.
            logger.warning(
                'Org %s is set to Postal but has no sending-enabled domain; '
                'falling back to the platform default.', organization.id
            )
            return get_connection()

        if provider == 'platform_default':
            return (
                EmailConfigService.get_postal_connection(organization)
                or get_connection()
            )

        if provider == 'smtp' and config.smtp_host:
            return get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=config.smtp_host,
                port=config.smtp_port,
                username=config.smtp_username,
                password=config.smtp_password,
                use_tls=config.smtp_use_tls,
                use_ssl=config.smtp_use_ssl,
                fail_silently=False,
            )

        if provider == 'sendgrid' and config.api_key:
            # SendGrid supports SMTP relay with API key as password
            return get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host='smtp.sendgrid.net',
                port=587,
                username='apikey',
                password=config.api_key,
                use_tls=True,
                use_ssl=False,
                fail_silently=False,
            )

        if provider == 'mailgun' and config.api_key and config.provider_domain:
            return get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host='smtp.mailgun.org',
                port=587,
                username=f'postmaster@{config.provider_domain}',
                password=config.api_key,
                use_tls=True,
                use_ssl=False,
                fail_silently=False,
            )

        if provider == 'ses' and config.api_key:
            # SES SMTP: api_key stores "ACCESS_KEY_ID:SECRET_ACCESS_KEY" or just the SMTP password
            # SES SMTP endpoint varies by region
            region = config.provider_region or 'us-east-1'
            host = f'email-smtp.{region}.amazonaws.com'
            # api_key format: "SMTP_USER::SMTP_PASS"
            parts = config.api_key.split('::', 1)
            smtp_user = parts[0] if len(parts) == 2 else ''
            smtp_pass = parts[1] if len(parts) == 2 else config.api_key
            return get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=host,
                port=587,
                username=smtp_user,
                password=smtp_pass,
                use_tls=True,
                use_ssl=False,
                fail_silently=False,
            )

        # platform_default or misconfigured
        return get_connection()

    @staticmethod
    def get_default_from(organization, fallback_name='', fallback_email=''):
        """
        Return (from_name, from_email) using org's email config, with fallbacks.
        """
        from .models import EmailConfiguration
        try:
            config = EmailConfiguration.objects.get(organization=organization)
            name = config.from_name or fallback_name or 'Team'
            email = config.from_email or fallback_email or django_settings.DEFAULT_FROM_EMAIL
            return name, email
        except EmailConfiguration.DoesNotExist:
            return (
                fallback_name or 'Team',
                fallback_email or django_settings.DEFAULT_FROM_EMAIL,
            )

    @staticmethod
    def get_footer_html(organization):
        """Return the configured compliance footer text for injecting into emails."""
        from .models import EmailConfiguration
        try:
            config = EmailConfiguration.objects.get(organization=organization)
            address = config.physical_address.strip()
            footer = config.email_footer_text.strip()
            parts = []
            if footer:
                parts.append(footer)
            if address:
                parts.append(address)
            return '<br>'.join(parts)
        except EmailConfiguration.DoesNotExist:
            return ''

    @staticmethod
    def test_connection(organization, to_email):
        """
        Send a test email using the org's configured backend.
        Returns (success: bool, message: str).
        """
        from_name, from_email = EmailConfigService.get_default_from(organization)
        try:
            connection = EmailConfigService.get_connection(organization)
            msg = EmailMessage(
                subject='Email Configuration Test',
                body=(
                    'This is a test email from your Email Marketing Platform.\n\n'
                    'If you received this, your email configuration is working correctly.'
                ),
                from_email=f'{from_name} <{from_email}>',
                to=[to_email],
                connection=connection,
            )
            msg.send(fail_silently=False)
            return True, f'Test email sent successfully to {to_email}'
        except Exception as exc:
            logger.exception(f'Email config test failed for org {organization.id}: {exc}')
            return False, str(exc)

    @staticmethod
    def verify_domain(sending_domain):
        """
        Run the authoritative DNS check for a sending domain.

        Delegates to the provisioning API, which queries the domain's own
        nameservers and enables sending only when SPF, DKIM, return-path and
        DMARC all pass.

        This replaced a local check that resolved TXT records with dnspython and
        treated "no records found" as success — and since dnspython was never a
        dependency, that meant every domain was marked verified without a single
        lookup. Domain ownership is now proven against DNS, not assumed.
        """
        from .provisioning import PostalProvisioningService
        return PostalProvisioningService.check_domain(sending_domain)

    @staticmethod
    def check_sending_limits(organization):
        """
        Returns (allowed: bool, reason: str).
        Checks daily/hourly limits and threshold pausing.
        """
        from .models import EmailConfiguration
        from apps.campaigns.models import CampaignRecipient

        # Account suspension implies sending suspension. Checked before the
        # EmailConfiguration lookup so it applies even to an organization that
        # has never opened the email settings page.
        if not organization.is_active:
            reason = (organization.suspension_reason or '').strip()
            return False, f'Account suspended. {reason}'.strip()

        try:
            config = EmailConfiguration.objects.get(organization=organization)
        except EmailConfiguration.DoesNotExist:
            return True, ''

        if config.sending_paused_due_to_threshold:
            return False, (
                config.sending_pause_reason
                or 'Sending paused: bounce or complaint rate exceeded threshold.'
            )

        now = timezone.now()

        if config.daily_send_limit > 0:
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            sent_today = CampaignRecipient.objects.filter(
                campaign__organization=organization,
                sent_at__gte=day_start,
            ).count()
            if sent_today >= config.daily_send_limit:
                return False, f'Daily send limit of {config.daily_send_limit} reached.'

        if config.hourly_send_limit > 0:
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            sent_this_hour = CampaignRecipient.objects.filter(
                campaign__organization=organization,
                sent_at__gte=hour_start,
            ).count()
            if sent_this_hour >= config.hourly_send_limit:
                return False, f'Hourly send limit of {config.hourly_send_limit} reached.'

        return True, ''
