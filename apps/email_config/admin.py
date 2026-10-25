from django.contrib import admin
from .models import EmailConfiguration, PostalTenant, SendingDomain


@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ['organization', 'provider', 'from_email', 'sending_paused_due_to_threshold', 'updated_at']
    list_filter = ['provider', 'sending_paused_due_to_threshold']
    search_fields = ['organization__name', 'from_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Organization', {'fields': ('id', 'organization')}),
        ('Sending Identity', {'fields': ('from_name', 'from_email', 'reply_to_email')}),
        ('Provider', {'fields': (
            'provider', 'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password',
            'smtp_use_tls', 'smtp_use_ssl', 'api_key', 'provider_domain', 'provider_region',
        )}),
        ('Compliance', {'fields': ('physical_address', 'email_footer_text', 'unsubscribe_redirect_url')}),
        ('Limits', {'fields': ('daily_send_limit', 'hourly_send_limit')}),
        ('Thresholds', {'fields': ('bounce_threshold_pct', 'complaint_threshold_pct', 'sending_paused_due_to_threshold')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(SendingDomain)
class SendingDomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'organization', 'status', 'sending_enabled',
                    'verified_at', 'last_check_at']
    list_filter = ['status', 'sending_enabled']
    search_fields = ['domain', 'organization__name']
    readonly_fields = ['id', 'dns_records', 'sending_enabled', 'spf_record',
                       'dkim_selector', 'dkim_record_name', 'dkim_record_value',
                       'verified_at', 'last_check_at', 'last_check_error',
                       'created_at', 'updated_at']


@admin.register(PostalTenant)
class PostalTenantAdmin(admin.ModelAdmin):
    list_display = ['external_id', 'organization', 'status', 'send_limit_per_hour',
                    'queued', 'held', 'bounce_rate_30d', 'last_synced_at']
    list_filter = ['status', 'ip_pool']
    search_fields = ['external_id', 'postal_tenant_id', 'organization__name']
    # external_id is the provisioner's key for this mail server and api_key is
    # unrecoverable once set, so neither is editable here. Rotate the key
    # through the provisioning API instead.
    readonly_fields = ['id', 'external_id', 'postal_tenant_id', 'api_key',
                       'sent_last_hour', 'queued', 'held', 'bounce_rate_30d',
                       'last_synced_at', 'last_error', 'created_at', 'updated_at']
