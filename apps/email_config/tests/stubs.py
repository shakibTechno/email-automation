"""
Stand-ins for the provisioning API and the Postal send API.

Every test in this package runs against these rather than a live server, so the
suite needs no Postal instance, no network, and no credentials.
"""
from apps.email_config.provisioner_client import ProvisionerError


def dns_records(spf='OK', dkim='OK', return_path='OK', dmarc='OK', name='news.acme.com'):
    """Build a provisioner records[] payload with the given per-record statuses."""
    return [
        {'purpose': 'spf', 'type': 'TXT', 'host': name,
         'value': 'v=spf1 include:spf.mail.platform.test ~all',
         'status': spf, 'error': None if spf == 'OK' else 'No SPF record found',
         'note': 'Only one SPF record is allowed per domain.'},
        {'purpose': 'dkim', 'type': 'TXT', 'host': f'postal-ABCDEF._domainkey.{name}',
         'value': 'v=DKIM1; t=s; h=sha256; p=MIIBIjANBgkq',
         'status': dkim, 'error': None if dkim == 'OK' else 'DKIM record does not match',
         'note': 'Long value: paste it as one value.'},
        {'purpose': 'return_path', 'type': 'CNAME', 'host': f'psrp.{name}',
         'value': 'rp.mail.platform.test',
         'status': return_path,
         'error': None if return_path == 'OK' else 'No return-path CNAME found',
         'note': 'Lets bounces come back to the platform.'},
        {'purpose': 'dmarc', 'type': 'TXT', 'host': f'_dmarc.{name}',
         'value': 'v=DMARC1; p=none;',
         'status': dmarc, 'error': None if dmarc == 'OK' else 'No DMARC record found',
         'note': 'Required by Gmail and Yahoo for bulk mail.'},
    ]


class FakeProvisioner:
    """
    In-memory provisioning API.

    Mirrors the real contract where it matters: api_key is returned only on
    create and rotation, external_id is unique, domains are idempotent, and
    sending is enabled only when all four DNS records pass.
    """

    def __init__(self):
        self.tenants = {}          # postal_tenant_id -> dict
        self.domains = {}          # (tenant_id, name) -> dict
        self.suppressions = []     # (tenant_id, address, reason)
        self.calls = []            # every method call, for assertions
        self.next_id = 1
        self.dns_result = dns_records()
        self.fail_with = None      # set to a ProvisionerError to force failure

    # ------------------------------------------------------------------ helpers
    def _record(self, name, *args):
        self.calls.append((name, *args))
        if self.fail_with:
            raise self.fail_with

    def call_names(self):
        return [call[0] for call in self.calls]

    @property
    def is_configured(self):
        return True

    # ------------------------------------------------------------------ tenants
    def create_tenant(self, external_id, name, send_limit_per_hour=None, ip_pool=None):
        self._record('create_tenant', external_id)
        if any(t['external_id'] == external_id for t in self.tenants.values()):
            raise ProvisionerError(409, 'tenant_exists', 'already exists')
        tenant_id = f'tenant-{self.next_id}'
        self.next_id += 1
        self.tenants[tenant_id] = {
            'id': tenant_id, 'external_id': external_id, 'name': name,
            'status': 'Live', 'suspended': False, 'suspension_reason': None,
            'send_limit_per_hour': send_limit_per_hour, 'ip_pool': ip_pool,
        }
        return {**self.tenants[tenant_id], 'api_key': f'key-{tenant_id}'}

    def find_tenant(self, external_id):
        self._record('find_tenant', external_id)
        for tenant in self.tenants.values():
            if tenant['external_id'] == external_id:
                return dict(tenant)
        raise ProvisionerError(404, 'tenant_not_found', 'no such tenant')

    def get_tenant(self, tenant_id):
        self._record('get_tenant', tenant_id)
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            raise ProvisionerError(404, 'tenant_not_found', 'no such tenant')
        return {
            **tenant,
            'sent_last_hour': 12, 'queued': 3, 'held': 1, 'bounce_rate_30d': 1.25,
            'domains': [
                {'name': key[1], 'sending_enabled': value['sending_enabled']}
                for key, value in self.domains.items() if key[0] == tenant_id
            ],
        }

    def update_tenant(self, tenant_id, send_limit_per_hour=..., ip_pool=...):
        self._record('update_tenant', tenant_id)
        tenant = self.tenants[tenant_id]
        if send_limit_per_hour is not ...:
            tenant['send_limit_per_hour'] = send_limit_per_hour
        if ip_pool is not ...:
            tenant['ip_pool'] = ip_pool
        return dict(tenant)

    def suspend(self, tenant_id, reason):
        self._record('suspend', tenant_id, reason)
        self.tenants[tenant_id].update(suspended=True, suspension_reason=reason)
        return dict(self.tenants[tenant_id])

    def unsuspend(self, tenant_id):
        self._record('unsuspend', tenant_id)
        self.tenants[tenant_id].update(suspended=False, suspension_reason=None)
        return dict(self.tenants[tenant_id])

    def delete_tenant(self, tenant_id):
        self._record('delete_tenant', tenant_id)
        self.tenants.pop(tenant_id, None)
        return {'deleted': True}

    def rotate_api_key(self, tenant_id, revoke_old=True):
        self._record('rotate_api_key', tenant_id)
        return {'api_key': f'rotated-{tenant_id}'}

    # ------------------------------------------------------------------ domains
    def add_domain(self, tenant_id, name):
        self._record('add_domain', tenant_id, name)
        key = (tenant_id, name)
        if key not in self.domains:
            self.domains[key] = {'name': name, 'sending_enabled': False,
                                 'records': self.dns_result}
        return dict(self.domains[key])

    def get_domain(self, tenant_id, name):
        self._record('get_domain', tenant_id, name)
        return dict(self.domains[(tenant_id, name)])

    def check_domain(self, tenant_id, name):
        self._record('check_domain', tenant_id, name)
        key = (tenant_id, name)
        if key not in self.domains:
            raise ProvisionerError(404, 'domain_not_found', 'no such domain')
        # The real provisioner enables sending only when every record passes.
        enabled = all(r['status'] == 'OK' for r in self.dns_result)
        self.domains[key].update(sending_enabled=enabled, records=self.dns_result)
        return dict(self.domains[key])

    def delete_domain(self, tenant_id, name):
        self._record('delete_domain', tenant_id, name)
        self.domains.pop((tenant_id, name), None)
        return {'deleted': True}

    # -------------------------------------------------------------- suppressions
    def suppress(self, tenant_id, address, reason=None, days=None):
        self._record('suppress', tenant_id, address, reason)
        self.suppressions.append((tenant_id, address, reason))
        return {'address': address, 'suppressed_days': days or 3650}

    def unsuppress(self, tenant_id, address):
        self._record('unsuppress', tenant_id, address)
        return {'removed': True}

    def list_suppressions(self, tenant_id, page=1):
        self._record('list_suppressions', tenant_id)
        return {'page': page, 'total_pages': 1, 'total': len(self.suppressions),
                'suppressions': []}


class FakePostal:
    """
    Records what would have been sent, and hands back ids the way Postal does.

    `sent` holds one entry per API call, which is what the one-call-per-recipient
    assertions check.
    """

    def __init__(self):
        self.sent = []
        self.next_id = 1000
        self.error = None

    def __call__(self, *, api_key, to, from_, subject, html, text=None,
                 reply_to=None, tag=None, headers=None, attachments=None,
                 base_url=None, timeout=None):
        if self.error:
            raise self.error
        self.sent.append({
            'api_key': api_key, 'to': to, 'from': from_, 'subject': subject,
            'html': html, 'text': text, 'reply_to': reply_to, 'tag': tag,
            'headers': dict(headers or {}), 'attachments': attachments,
        })
        postal_id = self.next_id
        self.next_id += 1
        return {'message_id': f'<{postal_id}@rp.mail.platform.test>',
                'postal_id': postal_id, 'token': f'tok{postal_id}'}
