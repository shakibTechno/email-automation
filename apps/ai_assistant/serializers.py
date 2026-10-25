"""
Serializers for the AI Assistant app.
"""
from rest_framework import serializers

from .models import AIConfiguration, GenerationJob
from .providers import default_model_for


class AIConfigurationSerializer(serializers.ModelSerializer):
    """
    Read view of the connection. The key is never returned — only whether one
    is saved — matching how EmailConfiguration masks its provider secrets.
    """

    api_key_set = serializers.SerializerMethodField()
    effective_model = serializers.SerializerMethodField()
    # Lets the UI ask for an address instead of a key without hard-coding
    # which providers are self-hosted.
    requires_api_key = serializers.SerializerMethodField()
    is_ready = serializers.BooleanField(read_only=True)

    class Meta:
        model = AIConfiguration
        fields = [
            'id', 'provider', 'model', 'effective_model', 'base_url',
            'api_key_set', 'requires_api_key', 'is_enabled', 'is_ready',
            'last_validated_at', 'last_error',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_api_key_set(self, obj):
        return bool(obj.api_key)

    def get_effective_model(self, obj):
        return obj.model or default_model_for(obj.provider)

    def get_requires_api_key(self, obj):
        return obj.provider not in AIConfiguration.SELF_HOSTED_PROVIDERS


class AIConfigurationUpdateSerializer(serializers.ModelSerializer):
    """
    Write view. A blank `api_key` means "leave the stored one alone", so the
    client can save other settings without having to re-send the secret.
    """

    api_key = serializers.CharField(
        required=False, allow_blank=True, write_only=True, max_length=512,
    )

    class Meta:
        model = AIConfiguration
        fields = ['provider', 'model', 'base_url', 'api_key', 'is_enabled']

    def update(self, instance, validated_data):
        api_key = validated_data.pop('api_key', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if api_key:
            instance.api_key = api_key
            # A new key has not been tested yet; don't let an old success
            # vouch for it.
            instance.last_validated_at = None
            instance.last_error = ''

        instance.save()
        return instance


class GenerationJobSerializer(serializers.ModelSerializer):
    """What the client polls while a generation runs."""

    # `kind` plus `result_id` is all the client needs to know where to go next,
    # without it having to understand four different foreign keys.
    result_id = serializers.CharField(read_only=True)

    class Meta:
        model = GenerationJob
        fields = [
            'id', 'kind', 'status', 'prompt', 'audience',
            'result_id', 'landing_page', 'form', 'email_template', 'campaign',
            'error_message', 'was_sanitized',
            'provider', 'model', 'input_tokens', 'output_tokens',
            'created_at', 'started_at', 'finished_at',
        ]
        read_only_fields = fields


class GenerationRequestSerializer(serializers.Serializer):
    """The generation request body, whatever is being generated."""

    prompt = serializers.CharField(min_length=10, max_length=2000, trim_whitespace=True)
    audience = serializers.CharField(
        required=False, allow_blank=True, max_length=255, trim_whitespace=True,
    )


#: The name this serializer had when landing pages were the only kind.
PageGenerationRequestSerializer = GenerationRequestSerializer
