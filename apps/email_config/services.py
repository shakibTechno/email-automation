"""
Services for per-organization email configuration.
"""
import logging
from dataclasses import dataclass

from django.utils import timezone
from django.core.mail import get_connection, EmailMessage
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SendingIdentity:
    """
    Everything needed to send one message as an organization: the backend and
    the From address that backend will actually accept.

    These two used to be resolved by separate calls, and every sender paired
    them by hand. They can disagree — a connection that fell back to the shared
    sender with a From on the organization's own domain is rejected by Postal
    with UnauthenticatedFromAddress — so they are resolved together here and
    never apart.
    """
    connection: object
    from_name: str
    from_email: str
    reply_to: str
    is_shared: bool
    # Empty when this organization can send. Otherwise a sentence written for
    # the person reading it in Settings, not a socket error.
    unavailable: str = ''

    def sender(self, name='', email='', reply_to=''):
        """
        Return (From header, reply_to list) for one message, applying a
        per-message sender override where the identity can honour it.

        On the shared identity the requested address cannot be used — Postal
        only accepts a From whose domain it has verified for that tenant — so it
        becomes the reply address instead of being silently dropped. The display
        name is free text and is always honoured, so the recipient still sees
        who the mail is from.
        """
        display = name or self.from_name
        if self.is_shared:
            address = self.from_email
            back = reply_to or email or self.reply_to
        else:
            address = email or self.from_email
            back = reply_to or self.reply_to
        header = f'{display} <{address}>' if display else address
        return header, ([back] if back else None)


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
    def get_shared_connection():
        """
        Return a backend for the platform's own Postal tenant, or None.

        This is the shared identity an organization sends through before it has
        a verified domain of its own — what the provider picker calls "Platform
        Default". Its send limit lives on the Postal tenant rather than here, so
        a shared sender cannot be throttled by editing application config.
        """
        if not django_settings.POSTAL_ENABLED or not django_settings.POSTAL_URL:
            return None
        if not django_settings.POSTAL_SHARED_API_KEY:
            return None
        if not django_settings.POSTAL_SHARED_FROM_EMAIL:
            # Without a From address on the platform's own verified domain the
            # key is useless: Postal would reject every message.
            return None

        from .backends import PostalEmailBackend

        return PostalEmailBackend(
            api_key=django_settings.POSTAL_SHARED_API_KEY, fail_silently=False
        )

    @staticmethod
    def default_backend_is_configured():
        """
        Whether Django's own EMAIL_* settings point at something real.

        The SMTP default is localhost:25, which is nothing inside a container.
        Falling back to it is what turned "this organization has no sending
        domain" into "[Errno 111] Connection refused". A non-SMTP backend
        (console, locmem, file) is always real — it is only ever set
        deliberately — and so is SMTP with a host that was actually chosen.
        """
        backend = django_settings.EMAIL_BACKEND
        if not backend.endswith('smtp.EmailBackend'):
            return True
        host = (django_settings.EMAIL_HOST or '').strip()
        return bool(host) and host not in ('localhost', '127.0.0.1')

    @staticmethod
    def verified_sending_domains(organization):
        """The domains Postal will accept a From address on for this org."""
        from .models import SendingDomain
        return {
            d.lower()
            for d in SendingDomain.objects.filter(
                organization=organization, sending_enabled=True
            ).values_list('domain', flat=True)
        }

    @staticmethod
    def resolve(organization):
        """
        Return the SendingIdentity for this organization.

        Order:
          * the organization's own Postal tenant, when a verified domain backs
            the configured From address
          * the platform's shared identity, for 'postal' and 'platform_default'
          * the organization's own provider credentials (SMTP, SendGrid, …)
          * an identity with no connection and a reason the user can act on
        """
        from .models import EmailConfiguration

        config = EmailConfiguration.objects.filter(organization=organization).first()
        provider = config.provider if config else 'platform_default'
        name = (config.from_name if config else '') or organization.name or 'Team'
        email = (config.from_email if config else '')
        reply = (config.reply_to_email if config else '')

        def shared_or_unavailable():
            shared = EmailConfigService.get_shared_connection()
            if shared:
                # Replies go to whatever the organization asked to send as, so
                # a shared From does not strand the conversation.
                return SendingIdentity(
                    shared, name, django_settings.POSTAL_SHARED_FROM_EMAIL,
                    reply or email, True,
                )
            if EmailConfigService.default_backend_is_configured():
                # A deployment that runs its own mail server is a legitimate
                # platform default, and was the behaviour before the shared
                # identity existed.
                return SendingIdentity(
                    get_connection(), name,
                    email or django_settings.DEFAULT_FROM_EMAIL, reply, False,
                )
            return SendingIdentity(
                None, name, email, reply, False,
                'No sending identity is available yet. Add and verify a sending '
                'domain under Domain Authentication below, then set a From '
                'address on that domain.',
            )

        if provider in ('postal', 'platform_default'):
            own = EmailConfigService.get_postal_connection(organization)
            if own:
                verified = EmailConfigService.verified_sending_domains(organization)
                if not email and verified:
                    # Verified a domain but never chose a From address — the
                    # usual state straight after onboarding. Send from the
                    # domain they verified rather than treating them as unable
                    # to send at all.
                    email = f'noreply@{sorted(verified)[0]}'
                if email.rpartition('@')[2].lower() in verified:
                    return SendingIdentity(own, name, email, reply, False)
                # A verified domain exists but the From does not sit on it —
                # usually a From left behind by a domain that was removed.
                # Postal would reject this outright, so use the shared sender
                # and say so, rather than failing at send time.
                logger.warning(
                    'Org %s has a verified sending domain but its From address '
                    '%r is not on one; using the shared identity.',
                    organization.id, email,
                )
            return shared_or_unavailable()

        if provider == 'smtp' and not config.smtp_host:
            return SendingIdentity(
                None, name, email, reply, False,
                'SMTP is selected but no server address is configured.',
            )
        if provider in ('sendgrid', 'mailgun', 'ses') and not config.api_key:
            return SendingIdentity(
                None, name, email, reply, False,
                f'{provider.title()} is selected but no API key is configured.',
            )

        own = EmailConfigService._provider_connection(config)
        if own is None:
            return SendingIdentity(
                None, name, email, reply, False,
                f'{provider} is selected but its settings are incomplete.',
            )
        return SendingIdentity(
            own, name, email or django_settings.DEFAULT_FROM_EMAIL, reply, False
        )

    @staticmethod
    def get_connection(organization):
        """
        The organization's backend, or Django's default.

        Kept as the narrow view onto resolve() for callers that only send and
        never set a From address of their own.
        """
        return EmailConfigService.resolve(organization).connection or get_connection()

    @staticmethod
    def _provider_connection(config):
        """Build a connection from the organization's own provider credentials."""
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

        # Credentials present but incomplete for the selected provider.
        return None

    @staticmethod
    def get_default_from(organization, fallback_name='', fallback_email=''):
        """
        Return (from_name, from_email) for this organization.

        The narrow view onto resolve() for callers that do not set a sender of
        their own. Callers that do must use resolve().sender(), so the address
        stays one the resolved backend will accept.
        """
        identity = EmailConfigService.resolve(organization)
        return (
            identity.from_name or fallback_name or 'Team',
            identity.from_email or fallback_email or django_settings.DEFAULT_FROM_EMAIL,
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
        identity = EmailConfigService.resolve(organization)
        # Answer the question the user actually asked before opening a socket.
        # Without this the no-identity case surfaced as "[Errno 111] Connection
        # refused" from Django's unconfigured default SMTP backend, which says
        # nothing about the sending domain that is really missing.
        if identity.unavailable:
            return False, identity.unavailable

        from_header, reply_to = identity.sender()
        try:
            msg = EmailMessage(
                subject='Email Configuration Test',
                body=(
                    'This is a test email from your Email Marketing Platform.\n\n'
                    'If you received this, your email configuration is working correctly.'
                ),
                from_email=from_header,
                to=[to_email],
                reply_to=reply_to,
                connection=identity.connection,
            )
            msg.send(fail_silently=False)
        except Exception as exc:
            logger.exception(f'Email config test failed for org {organization.id}: {exc}')
            return False, str(exc)

        if identity.is_shared:
            return True, (
                f'Test email sent to {to_email} from the shared platform address '
                f'{identity.from_email}. Verify a sending domain of your own to '
                f'send as your brand.'
            )
        return True, f'Test email sent successfully to {to_email}'

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
