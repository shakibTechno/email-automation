"""
Serializers for the Email Templates app.
"""
from rest_framework import serializers
from .models import EmailTemplate, TemplateImage


class EmailTemplateListSerializer(serializers.ModelSerializer):
    """Serializer for template list view (minimal fields)."""

    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'category', 'subject', 'thumbnail_url',
            'is_preset', 'is_active', 'created_at', 'updated_at'
        ]


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Full serializer for EmailTemplate model."""

    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'description', 'category', 'subject',
            'design_json', 'html_content', 'thumbnail_url',
            'is_preset', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a template."""

    class Meta:
        model = EmailTemplate
        fields = [
            'name', 'description', 'category', 'subject',
            'design_json', 'html_content'
        ]

    def validate_name(self, value):
        """Validate name uniqueness within organization."""
        request = self.context.get('request')
        organization = request.user.organization

        if EmailTemplate.objects.filter(
            organization=organization, name=value
        ).exists():
            raise serializers.ValidationError(
                "A template with this name already exists in your organization."
            )
        return value


class EmailTemplateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a template."""

    class Meta:
        model = EmailTemplate
        fields = [
            'name', 'description', 'category', 'subject',
            'design_json', 'html_content', 'is_active'
        ]

    def validate_name(self, value):
        """Validate name uniqueness within organization."""
        request = self.context.get('request')
        organization = request.user.organization

        queryset = EmailTemplate.objects.filter(
            organization=organization, name=value
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A template with this name already exists in your organization."
            )
        return value


class TemplateImageSerializer(serializers.ModelSerializer):
    """Serializer for TemplateImage model."""

    class Meta:
        model = TemplateImage
        fields = [
            'id', 'image', 'original_filename',
            'file_size', 'width', 'height', 'created_at'
        ]
        read_only_fields = ['id', 'original_filename', 'file_size', 'width', 'height', 'created_at']
