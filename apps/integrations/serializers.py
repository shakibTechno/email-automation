"""
Serializers for the integrations app.
"""
from rest_framework import serializers
from .models import AnalyticsIntegration, SocialIntegration, LeadSyncLog


class AnalyticsIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsIntegration
        fields = [
            'id', 'provider', 'tracking_id', 'is_enabled', 'settings',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UpsertAnalyticsSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=AnalyticsIntegration.PROVIDER_CHOICES
    )
    tracking_id = serializers.CharField(max_length=100)
    is_enabled = serializers.BooleanField(default=True)
    settings = serializers.JSONField(required=False, default=dict)


class SocialIntegrationSerializer(serializers.ModelSerializer):
    default_tag_name = serializers.SerializerMethodField()
    connected_by_name = serializers.SerializerMethodField()
    has_credentials = serializers.SerializerMethodField()
    credentials_display = serializers.SerializerMethodField()

    class Meta:
        model = SocialIntegration
        fields = [
            'id', 'platform', 'status',
            'external_account_id', 'external_account_name',
            'auto_sync', 'sync_interval_minutes', 'last_synced_at',
            'field_mapping', 'default_tag', 'default_tag_name',
            'total_leads_imported', 'connected_by', 'connected_by_name',
            'is_demo', 'has_credentials', 'credentials_display',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'platform', 'status',
            'external_account_id', 'external_account_name',
            'last_synced_at', 'total_leads_imported',
            'connected_by', 'is_demo',
            'created_at', 'updated_at',
        ]

    def get_default_tag_name(self, obj):
        if obj.default_tag:
            return obj.default_tag.name
        return None

    def get_connected_by_name(self, obj):
        if obj.connected_by:
            full_name = f"{obj.connected_by.first_name} {obj.connected_by.last_name}".strip()
            return full_name or obj.connected_by.email
        return None

    def get_has_credentials(self, obj):
        creds = obj.credentials or {}
        return bool(creds.get('app_id') and creds.get('app_secret'))

    def get_credentials_display(self, obj):
        creds = obj.credentials or {}
        if not creds:
            return {}
        result = {}
        if creds.get('app_id'):
            result['app_id'] = creds['app_id']
        if creds.get('app_secret'):
            secret = creds['app_secret']
            result['app_secret'] = '••••' + secret[-4:] if len(secret) > 4 else '••••'
        if creds.get('page_id'):
            result['page_id'] = creds['page_id']
        if creds.get('organization_id'):
            result['organization_id'] = creds['organization_id']
        return result


class UpdateSocialIntegrationSerializer(serializers.Serializer):
    auto_sync = serializers.BooleanField(required=False)
    sync_interval_minutes = serializers.IntegerField(
        required=False, min_value=5, max_value=1440
    )
    field_mapping = serializers.JSONField(required=False)
    default_tag = serializers.UUIDField(required=False, allow_null=True)


class LeadSyncLogSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = LeadSyncLog
        fields = [
            'id', 'integration', 'status',
            'leads_found', 'leads_created', 'leads_updated', 'leads_failed',
            'error_message', 'error_details',
            'started_at', 'completed_at', 'duration_seconds',
            'created_at',
        ]
        read_only_fields = [
            'id', 'integration', 'status',
            'leads_found', 'leads_created', 'leads_updated', 'leads_failed',
            'error_message', 'error_details',
            'started_at', 'completed_at',
            'created_at',
        ]

    def get_duration_seconds(self, obj):
        if obj.completed_at and obj.started_at:
            delta = obj.completed_at - obj.started_at
            return round(delta.total_seconds(), 2)
        return None


class UpdateCredentialsSerializer(serializers.Serializer):
    app_id = serializers.CharField(max_length=255)
    app_secret = serializers.CharField(max_length=255)
    page_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    organization_id = serializers.CharField(max_length=255, required=False, allow_blank=True)


class DemoConnectSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(
        choices=SocialIntegration.PLATFORM_CHOICES
    )
