from django.contrib import admin
from .models import EmailConfiguration, SendingDomain


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
    list_display = ['domain', 'organization', 'status', 'verified_at', 'last_check_at']
    list_filter = ['status']
    search_fields = ['domain', 'organization__name']
    readonly_fields = ['id', 'spf_record', 'dkim_selector', 'dkim_record_name',
                       'dkim_record_value', 'verified_at', 'last_check_at', 'last_check_error', 'created_at', 'updated_at']
