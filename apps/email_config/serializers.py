"""
Serializers for email configuration.
"""
from rest_framework import serializers
from .models import EmailConfiguration, SendingDomain

_MASKED = '••••••••'


class EmailConfigSerializer(serializers.ModelSerializer):
    """Full read serializer — masks secrets."""
    smtp_password_set = serializers.SerializerMethodField()
    api_key_set = serializers.SerializerMethodField()

    class Meta:
        model = EmailConfiguration
        fields = [
            'id',
            # Identity
            'from_name', 'from_email', 'reply_to_email',
            # Provider
            'provider',
            'smtp_host', 'smtp_port', 'smtp_username',
            'smtp_password_set',   # bool — is password saved?
            'smtp_use_tls', 'smtp_use_ssl',
            'api_key_set',         # bool — is key saved?
            'provider_domain', 'provider_region',
            # Compliance
            'physical_address', 'email_footer_text', 'unsubscribe_redirect_url',
            # Limits
            'daily_send_limit', 'hourly_send_limit',
            # Thresholds
            'bounce_threshold_pct', 'complaint_threshold_pct',
            'sending_paused_due_to_threshold',
            'updated_at',
        ]
        read_only_fields = ['id', 'smtp_password_set', 'api_key_set',
                            'sending_paused_due_to_threshold', 'updated_at']

    def get_smtp_password_set(self, obj):
        return bool(obj.smtp_password)

    def get_api_key_set(self, obj):
        return bool(obj.api_key)


class EmailConfigUpdateSerializer(serializers.ModelSerializer):
    """Write serializer — accepts plain-text secrets, skips blank-password no-ops."""

    # Optional secret fields: if omitted or empty string → keep existing value
    smtp_password = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
        style={'input_type': 'password'},
    )
    api_key = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = EmailConfiguration
        fields = [
            'from_name', 'from_email', 'reply_to_email',
            'provider',
            'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password',
            'smtp_use_tls', 'smtp_use_ssl',
            'api_key', 'provider_domain', 'provider_region',
            'physical_address', 'email_footer_text', 'unsubscribe_redirect_url',
            'daily_send_limit', 'hourly_send_limit',
            'bounce_threshold_pct', 'complaint_threshold_pct',
        ]

    def update(self, instance, validated_data):
        # Only overwrite secrets if a non-empty value was sent
        smtp_password = validated_data.pop('smtp_password', '')
        api_key = validated_data.pop('api_key', '')
        if smtp_password:
            instance.smtp_password = smtp_password
        if api_key:
            instance.api_key = api_key
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class SendingDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = SendingDomain
        fields = [
            'id', 'domain', 'status', 'verified_at',
            'spf_record',
            'dkim_selector', 'dkim_record_name', 'dkim_record_value',
            'last_check_at', 'last_check_error',
            'created_at',
        ]
        read_only_fields = [
            'id', 'status', 'verified_at',
            'spf_record', 'dkim_selector', 'dkim_record_name', 'dkim_record_value',
            'last_check_at', 'last_check_error', 'created_at',
        ]


class SendingDomainCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SendingDomain
        fields = ['domain']
