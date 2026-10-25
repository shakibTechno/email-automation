"""
Client for the mailstack provisioning API.

Ported from mailstack/examples/python/provisioner.py, which is written against
the real API and covered by mailstack/provisioner/test/app_test.rb. Adapted to
read its configuration from Django settings and to retry idempotent reads.

The provisioner creates one Postal mail server ("tenant") per organization,
adds that organization's sending domains, returns the exact DNS records the
customer must publish, and only enables sending once SPF, DKIM, return-path
and DMARC all pass. See mailstack/MULTI-TENANT.md §7 for the API reference.
"""
import logging
from urllib.parse import quote

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Idempotent verbs are safe to retry; POST/PATCH/DELETE are not.
_RETRY_METHODS = {'GET'}
_TIMEOUT = 30


class ProvisionerError(Exception):
    """
    An error returned by the provisioning API.

    `code` is the machine-readable code from the API body, e.g. 'tenant_exists',
    'domain_in_use', 'invalid_domain'. Callers branch on it rather than on the
    HTTP status, because several codes share a status.
    """

    def __init__(self, status, code, message=''):
        super().__init__(f'{status} {code}: {message}'.rstrip(': '))
        self.status = status
        self.code = code
        self.message = message


class ProvisionerNotConfigured(ProvisionerError):
    """Raised when POSTAL_PROVISIONER_URL / _TOKEN are not set."""

    def __init__(self):
        super().__init__(
            0, 'not_configured',
            'Postal provisioning is not configured. Set POSTAL_PROVISIONER_URL '
            'and POSTAL_PROVISIONER_TOKEN.',
        )


class ProvisionerClient:
    """
    Thin wrapper over the provisioning API.

    All methods raise ProvisionerError on a non-2xx response. `tenant_id` is the
    Postal server UUID returned by create_tenant / find_tenant, not the
    organization's own id.
    """

    def __init__(self, base_url=None, token=None, timeout=_TIMEOUT):
        self.base_url = (base_url or settings.POSTAL_PROVISIONER_URL or '').rstrip('/')
        self.token = token or settings.POSTAL_PROVISIONER_TOKEN
        self.timeout = timeout

    @property
    def is_configured(self):
        return bool(self.base_url and self.token)

    # ------------------------------------------------------------------ plumbing
    def _request(self, method, path, body=None):
        if not self.is_configured:
            raise ProvisionerNotConfigured()

        url = self.base_url + path
        attempts = 2 if method in _RETRY_METHODS else 1
        last_exc = None

        for attempt in range(attempts):
            try:
                response = requests.request(
                    method, url,
                    json=body,
                    headers={'Authorization': f'Bearer {self.token}'},
                    timeout=self.timeout,
                )
                break
            except requests.RequestException as exc:
                last_exc = exc
                if attempt + 1 >= attempts:
                    logger.warning('Provisioner %s %s unreachable: %s', method, path, exc)
                    raise ProvisionerError(0, 'unreachable', str(exc)) from exc
        else:  # pragma: no cover - the loop always breaks or raises
            raise ProvisionerError(0, 'unreachable', str(last_exc))

        try:
            data = response.json()
        except ValueError:
            data = {}

        if not response.ok:
            error = data.get('error') or {}
            raise ProvisionerError(
                response.status_code,
                error.get('code', 'http_error'),
                error.get('message', ''),
            )
        return data

    # ------------------------------------------------------------------- tenants
    def create_tenant(self, external_id, name, send_limit_per_hour=None, ip_pool=None):
        """
        Create a Postal mail server for one organization.

        The returned dict carries `api_key`, which the API returns ONLY here and
        on rotation — it cannot be read back later. Store it before returning.
        Raises ProvisionerError('tenant_exists') on a duplicate external_id.
        """
        return self._request('POST', '/tenants', {
            'external_id': external_id,
            'name': name,
            'send_limit': send_limit_per_hour,
            'ip_pool': ip_pool,
        })

    def get_tenant(self, tenant_id):
        """Detailed tenant info: sent_last_hour, queued, held, bounce_rate_30d, domains."""
        return self._request('GET', f'/tenants/{tenant_id}')

    def find_tenant(self, external_id):
        """Look a tenant up by our own external id. Raises 404 tenant_not_found."""
        return self._request('GET', f'/tenants?external_id={quote(external_id)}')

    def update_tenant(self, tenant_id, send_limit_per_hour=..., ip_pool=...):
        body = {}
        if send_limit_per_hour is not ...:
            body['send_limit'] = send_limit_per_hour
        if ip_pool is not ...:
            body['ip_pool'] = ip_pool
        return self._request('PATCH', f'/tenants/{tenant_id}', body)

    def suspend(self, tenant_id, reason):
        """Postal holds this tenant's mail while suspended. Other tenants are unaffected."""
        return self._request('POST', f'/tenants/{tenant_id}/suspend', {'reason': reason})

    def unsuspend(self, tenant_id):
        return self._request('POST', f'/tenants/{tenant_id}/unsuspend')

    def delete_tenant(self, tenant_id):
        return self._request('DELETE', f'/tenants/{tenant_id}')

    def rotate_api_key(self, tenant_id, revoke_old=True):
        """Pass revoke_old=False for a zero-downtime swap, then rotate again."""
        return self._request(
            'POST', f'/tenants/{tenant_id}/api-key/rotate', {'revoke_old': revoke_old}
        )

    # ------------------------------------------------------------------- domains
    def list_domains(self, tenant_id):
        return self._request('GET', f'/tenants/{tenant_id}/domains')

    def add_domain(self, tenant_id, name):
        """
        Add a sending domain and get back the DNS records to publish.

        Idempotent: repeating the call returns the existing domain. Raises
        'domain_not_allowed' for free mailbox domains and 'domain_in_use' (409)
        if another tenant has already verified it.
        """
        return self._request('POST', f'/tenants/{tenant_id}/domains', {'name': name})

    def get_domain(self, tenant_id, name):
        return self._request('GET', f'/tenants/{tenant_id}/domains/{quote(name)}')

    def check_domain(self, tenant_id, name):
        """
        Run every DNS check and turn sending on or off for the domain.

        This is the authoritative check: it queries the domain's own
        nameservers. `sending_enabled` in the response is true only when SPF,
        DKIM, return-path and DMARC all pass.
        """
        return self._request('POST', f'/tenants/{tenant_id}/domains/{quote(name)}/check')

    def delete_domain(self, tenant_id, name):
        return self._request('DELETE', f'/tenants/{tenant_id}/domains/{quote(name)}')

    # -------------------------------------------------------------- suppressions
    def list_suppressions(self, tenant_id, page=1):
        return self._request('GET', f'/tenants/{tenant_id}/suppressions?page={page}')

    def suppress(self, tenant_id, address, reason=None, days=None):
        body = {'address': address, 'reason': reason}
        if days:
            body['days'] = days
        return self._request('POST', f'/tenants/{tenant_id}/suppressions', body)

    def unsuppress(self, tenant_id, address):
        return self._request(
            'DELETE', f'/tenants/{tenant_id}/suppressions/{quote(address, safe="")}'
        )


def get_provisioner():
    """Return a client built from Django settings."""
    return ProvisionerClient()
