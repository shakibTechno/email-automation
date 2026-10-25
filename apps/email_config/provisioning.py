"""
Provisioning a Postal mail server per organization.

The provisioning API is the source of truth for tenants and domains; the models
in this app mirror it so the UI can render without a round trip. Every method
here is written to be safely re-runnable, because a provisioning call that fails
halfway must not leave an organization unable to retry.
"""
import logging
import re
import uuid as uuid_lib

from django.conf import settings
from django.utils import timezone

from .models import PostalTenant, SendingDomain
from .provisioner_client import ProvisionerError, get_provisioner

logger = logging.getLogger(__name__)

# The provisioner enforces /\A[a-z0-9][a-z0-9-]{0,47}\z/ (app.rb:31).
# Python spells Ruby's \z as \Z.
_EXTERNAL_ID_RE = re.compile(r'\A[a-z0-9][a-z0-9-]{0,47}\Z')
# Leave room for the '-' plus 8 hex characters inside the 48-char budget.
_SLUG_BUDGET = 35

# Postal's own default when we have no plan to derive a limit from.
_FALLBACK_SEND_LIMIT = 200


def build_external_id(organization):
    """
    Build a provisioner-safe external id for an organization.

    Organization.slug cannot be used directly: SlugField(max_length=255) is far
    over the 48-character limit, Django's slugify permits underscores which the
    provisioner rejects, and slugify() of a non-Latin name returns ''. So the
    slug is sanitised and truncated for readability in the Postal UI, then
    suffixed with 8 hex characters of the organization's UUID for uniqueness.

    The result is stored immutably, so renaming an organization can never
    orphan its mail server.
    """
    raw = (organization.slug or '').lower()
    # Underscores are legal in a Django slug but not in an external id.
    stem = re.sub(r'[^a-z0-9-]', '-', raw).strip('-')[:_SLUG_BUDGET].strip('-')
    suffix = uuid_lib.UUID(str(organization.id)).hex[:8]
    candidate = f'{stem}-{suffix}' if stem else f'org-{suffix}'
    # A slug starting with a non-alnum character is stripped above, but guard
    # the contract rather than trusting the derivation.
    if not _EXTERNAL_ID_RE.match(candidate):
        candidate = f'org-{suffix}'
    return candidate


def resolve_send_limit(organization):
    """
    The per-tenant hourly send limit, derived from the organization's plan.

    Deliberately reads the billing Plan row rather than Organization.plan:
    Organization.PLAN_CHOICES has no 'business' entry even though
    BillingService.change_plan writes that value, so gating on the
    Organization field silently misclassifies Business customers.

    New organizations may have no Subscription at all (initialize_subscription()
    has no callers), so the free-tier fallback is the normal path, not an edge
    case.
    """
    monthly = None
    try:
        from apps.billing.models import Subscription
        subscription = (
            Subscription.objects.select_related('plan').filter(organization=organization).first()
        )
        if subscription and subscription.plan:
            monthly = subscription.plan.max_emails_per_month
    except Exception:  # pragma: no cover - billing app optional at import time
        logger.debug('Could not read plan limits for org %s', organization.id, exc_info=True)

    if not monthly:
        monthly = getattr(organization, 'max_emails_per_month', None) or 1000

    # Spread the monthly allowance over a 30-day month, then apply the
    # multiplier so the Postal limit sits above our own pace and only trips
    # when something has genuinely gone wrong.
    hourly = max(1, int(monthly / (30 * 24)))
    return max(_FALLBACK_SEND_LIMIT, hourly * settings.POSTAL_SEND_LIMIT_MULTIPLIER)


class PostalProvisioningService:
    """Create and maintain one Postal mail server per organization."""

    # ------------------------------------------------------------------ tenants
    @staticmethod
    def get_tenant(organization):
        """Return the organization's PostalTenant, or None."""
        return PostalTenant.objects.filter(organization=organization).first()

    @staticmethod
    def get_or_create_tenant(organization):
        """
        Return the organization's Postal tenant, creating it if needed.

        Idempotent in both directions: a local row with no remote tenant is
        repaired, and a remote tenant with no local row is adopted. A 409
        tenant_exists is treated as success, because it means a previous attempt
        created the mail server but failed before the api_key was stored — in
        which case the key is unrecoverable and must be rotated.
        """
        provisioner = get_provisioner()
        tenant = PostalProvisioningService.get_tenant(organization)

        if tenant and tenant.postal_tenant_id and tenant.api_key:
            return tenant

        external_id = tenant.external_id if tenant else build_external_id(organization)

        # Adopt an existing remote tenant if there is one.
        remote = None
        try:
            remote = provisioner.find_tenant(external_id)
        except ProvisionerError as exc:
            if exc.code != 'tenant_not_found':
                raise

        api_key = ''
        if remote is None:
            try:
                remote = provisioner.create_tenant(
                    external_id=external_id,
                    name=organization.name[:200] or external_id,
                    send_limit_per_hour=resolve_send_limit(organization),
                )
                api_key = remote.get('api_key', '')
            except ProvisionerError as exc:
                if exc.code != 'tenant_exists':
                    raise
                # Created by an earlier attempt. Re-fetch, then rotate to get a
                # usable key, since the original was never returned to us.
                remote = provisioner.find_tenant(external_id)

        if remote and not api_key:
            rotated = provisioner.rotate_api_key(remote['id'], revoke_old=True)
            api_key = rotated.get('api_key', '')

        tenant, _ = PostalTenant.objects.update_or_create(
            organization=organization,
            defaults={
                'external_id': external_id,
                'postal_tenant_id': remote['id'],
                'api_key': api_key,
                'status': (
                    PostalTenant.STATUS_SUSPENDED if remote.get('suspended')
                    else PostalTenant.STATUS_ACTIVE
                ),
                'suspension_reason': remote.get('suspension_reason') or '',
                'send_limit_per_hour': remote.get('send_limit_per_hour'),
                'ip_pool': remote.get('ip_pool') or '',
                'last_synced_at': timezone.now(),
                'last_error': '',
            },
        )
        logger.info('Provisioned Postal tenant %s for org %s', external_id, organization.id)
        return tenant

    @staticmethod
    def sync_tenant(tenant):
        """Refresh the cached Postal metrics on a tenant."""
        provisioner = get_provisioner()
        try:
            remote = provisioner.get_tenant(tenant.postal_tenant_id)
        except ProvisionerError as exc:
            tenant.last_error = str(exc)
            tenant.save(update_fields=['last_error', 'updated_at'])
            raise

        tenant.sent_last_hour = remote.get('sent_last_hour') or 0
        tenant.queued = remote.get('queued') or 0
        tenant.held = remote.get('held') or 0
        tenant.bounce_rate_30d = remote.get('bounce_rate_30d') or 0
        tenant.status = (
            PostalTenant.STATUS_SUSPENDED if remote.get('suspended')
            else PostalTenant.STATUS_ACTIVE
        )
        tenant.suspension_reason = remote.get('suspension_reason') or ''
        tenant.send_limit_per_hour = remote.get('send_limit_per_hour')
        tenant.ip_pool = remote.get('ip_pool') or ''
        tenant.last_synced_at = timezone.now()
        tenant.last_error = ''
        tenant.save(update_fields=[
            'sent_last_hour', 'queued', 'held', 'bounce_rate_30d', 'status',
            'suspension_reason', 'send_limit_per_hour', 'ip_pool',
            'last_synced_at', 'last_error', 'updated_at',
        ])

        # Remote domain state is authoritative for whether sending is allowed.
        for entry in remote.get('domains') or []:
            SendingDomain.objects.filter(
                organization=tenant.organization, domain=entry.get('name'),
            ).update(sending_enabled=bool(entry.get('sending_enabled')))
        return tenant

    @staticmethod
    def suspend(tenant, reason):
        """Suspend a tenant in Postal. Its mail is held; other tenants are unaffected."""
        get_provisioner().suspend(tenant.postal_tenant_id, reason[:250])
        tenant.status = PostalTenant.STATUS_SUSPENDED
        tenant.suspension_reason = reason[:250]
        tenant.save(update_fields=['status', 'suspension_reason', 'updated_at'])
        logger.warning('Suspended Postal tenant %s: %s', tenant.external_id, reason)
        return tenant

    @staticmethod
    def unsuspend(tenant):
        get_provisioner().unsuspend(tenant.postal_tenant_id)
        tenant.status = PostalTenant.STATUS_ACTIVE
        tenant.suspension_reason = ''
        tenant.save(update_fields=['status', 'suspension_reason', 'updated_at'])
        logger.info('Unsuspended Postal tenant %s', tenant.external_id)
        return tenant

    @staticmethod
    def update_send_limit(tenant, send_limit_per_hour):
        get_provisioner().update_tenant(
            tenant.postal_tenant_id, send_limit_per_hour=send_limit_per_hour
        )
        tenant.send_limit_per_hour = send_limit_per_hour
        tenant.save(update_fields=['send_limit_per_hour', 'updated_at'])
        return tenant

    # ------------------------------------------------------------------ domains
    @staticmethod
    def add_domain(organization, domain_name):
        """
        Register a sending domain and mirror the DNS records to publish.

        Provisions the organization's tenant on the way through: this is the
        lazy trigger, so an organization gets mail infrastructure the first time
        it actually intends to send.
        """
        tenant = PostalProvisioningService.get_or_create_tenant(organization)
        remote = get_provisioner().add_domain(tenant.postal_tenant_id, domain_name)
        return PostalProvisioningService._mirror_domain(organization, remote)

    @staticmethod
    def check_domain(sending_domain):
        """
        Run the authoritative DNS check and update sending state.

        Returns (sending_enabled, message). The provisioner queries the domain's
        own nameservers and enables sending only when SPF, DKIM, return-path and
        DMARC all pass; if a record later breaks, this turns sending back off.
        """
        organization = sending_domain.organization
        tenant = PostalProvisioningService.get_tenant(organization)
        if not tenant or not tenant.postal_tenant_id:
            message = 'This organization has no Postal mail server yet.'
            PostalProvisioningService._record_check_failure(sending_domain, message)
            return False, message

        try:
            remote = get_provisioner().check_domain(
                tenant.postal_tenant_id, sending_domain.domain
            )
        except ProvisionerError as exc:
            PostalProvisioningService._record_check_failure(sending_domain, str(exc))
            return False, str(exc)

        mirrored = PostalProvisioningService._mirror_domain(organization, remote)
        if mirrored.sending_enabled:
            return True, f'{mirrored.domain} is verified and can send.'

        pending = [
            r.get('purpose') for r in mirrored.dns_records
            if r.get('status') != 'OK'
        ]
        return False, (
            'Still waiting on: ' + ', '.join(p for p in pending if p)
            if pending else 'DNS records are not yet in place.'
        )

    @staticmethod
    def delete_domain(sending_domain):
        """Remove a domain from Postal. A missing remote domain is not an error."""
        tenant = PostalProvisioningService.get_tenant(sending_domain.organization)
        if tenant and tenant.postal_tenant_id:
            try:
                get_provisioner().delete_domain(
                    tenant.postal_tenant_id, sending_domain.domain
                )
            except ProvisionerError as exc:
                if exc.code != 'domain_not_found':
                    raise

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _mirror_domain(organization, remote):
        """Write a provisioner domain payload onto the local SendingDomain row."""
        name = remote['name']
        enabled = bool(remote.get('sending_enabled'))
        records = remote.get('records') or []
        errors = [
            f"{r.get('purpose')}: {r.get('error')}"
            for r in records if r.get('error')
        ]

        if enabled:
            status = SendingDomain.STATUS_VERIFIED
        elif errors:
            status = SendingDomain.STATUS_FAILED
        else:
            status = SendingDomain.STATUS_PENDING

        domain, _ = SendingDomain.objects.update_or_create(
            organization=organization,
            domain=name,
            defaults={
                'status': status,
                'sending_enabled': enabled,
                'dns_records': records,
                'verified_at': timezone.now() if enabled else None,
                'last_check_at': timezone.now(),
                'last_check_error': '; '.join(errors),
            },
        )
        return domain

    @staticmethod
    def _record_check_failure(sending_domain, message):
        sending_domain.status = SendingDomain.STATUS_FAILED
        sending_domain.sending_enabled = False
        sending_domain.last_check_at = timezone.now()
        sending_domain.last_check_error = message
        sending_domain.save(update_fields=[
            'status', 'sending_enabled', 'last_check_at', 'last_check_error', 'updated_at',
        ])
