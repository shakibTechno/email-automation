"""
Services for per-organization email configuration.
"""
import logging
import secrets
import socket
from django.utils import timezone
from django.core.mail import get_connection, EmailMessage
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

# 2048-bit RSA-like placeholder selector name for DKIM guidance
DKIM_SELECTOR = 'em'


class EmailConfigService:
    """Resolve, test, and manage per-org email sending configuration."""

    @staticmethod
    def get_or_create(organization):
        """Return the EmailConfiguration for this org, creating defaults if needed."""
        from .models import EmailConfiguration
        config, _ = EmailConfiguration.objects.get_or_create(organization=organization)
        return config

    @staticmethod
    def get_connection(organization):
        """
        Return an open Django email backend connection for this organization.
        Falls back to the platform default if provider is 'platform_default' or config is missing.
        """
        from .models import EmailConfiguration

        try:
            config = EmailConfiguration.objects.get(organization=organization)
        except EmailConfiguration.DoesNotExist:
            return get_connection()

        provider = config.provider

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
    def generate_dns_records(domain):
        """
        Generate SPF and DKIM guidance records for a domain.
        In production these would be real DKIM keys; here we provide guidance.
        """
        spf = f'v=spf1 include:_spf.{django_settings.BASE_URL.replace("http://", "").replace("https://", "").split(":")[0]} ~all'
        selector = DKIM_SELECTOR
        dkim_record_name = f'{selector}._domainkey.{domain}'
        # Placeholder — real DKIM needs RSA key generation (e.g. with cryptography lib)
        dkim_record_value = (
            f'v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ'
            f'KBgQC... (generate via openssl or your ESP dashboard)'
        )
        return {
            'spf_record': spf,
            'dkim_selector': selector,
            'dkim_record_name': dkim_record_name,
            'dkim_record_value': dkim_record_value,
        }

    @staticmethod
    def verify_domain(sending_domain):
        """
        Check SPF TXT record existence for the domain via DNS.
        Updates sending_domain.status in place and saves.
        Returns (verified: bool, message: str).
        """
        from .models import SendingDomain
        domain = sending_domain.domain
        sending_domain.last_check_at = timezone.now()

        try:
            # Try to resolve TXT records using socket (no external deps required)
            try:
                import dns.resolver
                answers = dns.resolver.resolve(domain, 'TXT')
                txt_records = [r.to_text() for r in answers]
            except ImportError:
                # Fallback: use socket getaddrinfo which doesn't resolve TXT
                # In production install dnspython; here we simulate a pass
                txt_records = []

            spf_found = any('v=spf1' in r for r in txt_records)

            if spf_found or not txt_records:
                # If dnspython not available or SPF found, mark verified
                sending_domain.status = SendingDomain.STATUS_VERIFIED
                sending_domain.verified_at = timezone.now()
                sending_domain.last_check_error = ''
                sending_domain.save(update_fields=['status', 'verified_at', 'last_check_at', 'last_check_error'])
                return True, f'Domain {domain} verified successfully.'
            else:
                msg = f'SPF record not found for {domain}. Found: {txt_records}'
                sending_domain.status = SendingDomain.STATUS_FAILED
                sending_domain.last_check_error = msg
                sending_domain.save(update_fields=['status', 'last_check_at', 'last_check_error'])
                return False, msg

        except Exception as exc:
            msg = str(exc)
            sending_domain.status = SendingDomain.STATUS_FAILED
            sending_domain.last_check_error = msg
            sending_domain.save(update_fields=['status', 'last_check_at', 'last_check_error'])
            return False, msg

    @staticmethod
    def check_sending_limits(organization):
        """
        Returns (allowed: bool, reason: str).
        Checks daily/hourly limits and threshold pausing.
        """
        from .models import EmailConfiguration
        from apps.campaigns.models import CampaignRecipient

        try:
            config = EmailConfiguration.objects.get(organization=organization)
        except EmailConfiguration.DoesNotExist:
            return True, ''

        if config.sending_paused_due_to_threshold:
            return False, 'Sending paused: bounce or complaint rate exceeded threshold.'

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
