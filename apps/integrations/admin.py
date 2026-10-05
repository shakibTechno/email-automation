from django.contrib import admin
from .models import AnalyticsIntegration, SocialIntegration, LeadSyncLog


@admin.register(AnalyticsIntegration)
class AnalyticsIntegrationAdmin(admin.ModelAdmin):
    list_display = ['organization', 'provider', 'tracking_id', 'is_enabled', 'created_at']
    list_filter = ['provider', 'is_enabled']
    search_fields = ['organization__name', 'tracking_id']
    raw_id_fields = ['organization']


@admin.register(SocialIntegration)
class SocialIntegrationAdmin(admin.ModelAdmin):
    list_display = [
        'organization', 'platform', 'status', 'external_account_name',
        'auto_sync', 'total_leads_imported', 'last_synced_at', 'is_demo',
    ]
    list_filter = ['platform', 'status', 'auto_sync', 'is_demo']
    search_fields = ['organization__name', 'external_account_name', 'external_account_id']
    raw_id_fields = ['organization', 'connected_by', 'default_tag']
    readonly_fields = ['access_token', 'refresh_token', 'token_expires_at']


@admin.register(LeadSyncLog)
class LeadSyncLogAdmin(admin.ModelAdmin):
    list_display = [
        'integration', 'status', 'leads_found', 'leads_created',
        'leads_updated', 'leads_failed', 'started_at', 'completed_at',
    ]
    list_filter = ['status']
    search_fields = ['integration__organization__name', 'error_message']
    raw_id_fields = ['integration']
    readonly_fields = ['started_at']
