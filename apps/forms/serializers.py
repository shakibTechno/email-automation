"""
Serializers for the Forms & Lead Capture app.
"""
from rest_framework import serializers
from django.db import transaction
from .models import (
    Form, FormField, FormSubmission, default_styling, default_branding,
    default_layout, default_display_rules, default_conditional_logic,
)
from apps.contacts.models import Tag
from apps.contacts.serializers import TagSerializer


class FormFieldSerializer(serializers.ModelSerializer):
    """Serializer for FormField model (nested within form serializers)."""

    class Meta:
        model = FormField
        fields = [
            'id', 'field_type', 'label', 'placeholder', 'help_text',
            'is_required', 'options', 'validation_rules', 'order',
            'contact_field_mapping', 'width', 'default_value',
            'section_description', 'conditional_logic', 'custom_styling'
        ]
        read_only_fields = ['id']

    def to_internal_value(self, data):
        # Ensure conditional_logic has proper defaults
        if 'conditional_logic' not in data or not data.get('conditional_logic'):
            data['conditional_logic'] = default_conditional_logic()
        return super().to_internal_value(data)


class FormListSerializer(serializers.ModelSerializer):
    """Serializer for form list view (minimal fields)."""

    class Meta:
        model = Form
        fields = [
            'id', 'name', 'status', 'form_type',
            'submission_count', 'created_at', 'updated_at'
        ]


class FormSerializer(serializers.ModelSerializer):
    """Full serializer for Form model."""

    fields = FormFieldSerializer(many=True, read_only=True)
    assign_tags = TagSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Form
        fields = [
            'id', 'name', 'description', 'status', 'form_type',
            'submit_button_text', 'success_message', 'redirect_url',
            'show_gdpr_consent', 'gdpr_consent_text',
            'styling', 'branding', 'layout', 'display_rules',
            'assign_tags', 'notification_emails',
            'submission_count', 'fields',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'submission_count', 'created_by',
            'created_at', 'updated_at'
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email


class FormCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a form with nested fields."""

    assign_tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        default=list,
    )
    fields = FormFieldSerializer(many=True)
    styling = serializers.JSONField(required=False, default=default_styling)
    branding = serializers.JSONField(required=False, default=default_branding)
    layout = serializers.JSONField(required=False, default=default_layout)
    display_rules = serializers.JSONField(
        required=False, default=default_display_rules
    )

    class Meta:
        model = Form
        fields = [
            'name', 'description', 'form_type',
            'submit_button_text', 'success_message', 'redirect_url',
            'show_gdpr_consent', 'gdpr_consent_text',
            'styling', 'branding', 'layout', 'display_rules',
            'assign_tag_ids', 'fields'
        ]

    def validate_assign_tag_ids(self, value):
        if value:
            request = self.context.get('request')
            org = request.user.organization
            tags = Tag.objects.filter(id__in=value, organization=org)
            if tags.count() != len(value):
                raise serializers.ValidationError(
                    "Some tags do not belong to your organization."
                )
        return value

    def validate_fields(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one field is required."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        tag_ids = validated_data.pop('assign_tag_ids', [])
        fields_data = validated_data.pop('fields', [])

        form = Form.objects.create(**validated_data)

        # Bulk create form fields
        form_fields = []
        for idx, field_data in enumerate(fields_data):
            field_data.pop('id', None)
            form_fields.append(FormField(
                form=form,
                order=field_data.get('order', idx),
                **{k: v for k, v in field_data.items() if k != 'order'}
            ))
        FormField.objects.bulk_create(form_fields)

        # Set M2M tags
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            form.assign_tags.set(tags)

        return form


class FormUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a form with nested fields."""

    assign_tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
    )
    fields = FormFieldSerializer(many=True, required=False)
    styling = serializers.JSONField(required=False)
    branding = serializers.JSONField(required=False)
    layout = serializers.JSONField(required=False)
    display_rules = serializers.JSONField(required=False)

    class Meta:
        model = Form
        fields = [
            'name', 'description', 'status', 'form_type',
            'submit_button_text', 'success_message', 'redirect_url',
            'show_gdpr_consent', 'gdpr_consent_text',
            'styling', 'branding', 'layout', 'display_rules',
            'assign_tag_ids', 'fields'
        ]

    def validate_assign_tag_ids(self, value):
        if value:
            request = self.context.get('request')
            org = request.user.organization
            tags = Tag.objects.filter(id__in=value, organization=org)
            if tags.count() != len(value):
                raise serializers.ValidationError(
                    "Some tags do not belong to your organization."
                )
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('assign_tag_ids', None)
        fields_data = validated_data.pop('fields', None)

        # Update form scalar fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace fields if provided (delete + recreate)
        if fields_data is not None:
            instance.fields.all().delete()
            form_fields = []
            for idx, field_data in enumerate(fields_data):
                field_data.pop('id', None)
                form_fields.append(FormField(
                    form=instance,
                    order=field_data.get('order', idx),
                    **{k: v for k, v in field_data.items() if k != 'order'}
                ))
            FormField.objects.bulk_create(form_fields)

        # Update M2M tags
        if tag_ids is not None:
            tags = Tag.objects.filter(id__in=tag_ids)
            instance.assign_tags.set(tags)

        return instance


class PublicFormSerializer(serializers.ModelSerializer):
    """Serializer for public (unauthenticated) form rendering."""

    fields = FormFieldSerializer(many=True, read_only=True)

    class Meta:
        model = Form
        fields = [
            'id', 'name', 'description', 'form_type',
            'submit_button_text', 'show_gdpr_consent',
            'gdpr_consent_text', 'styling', 'branding', 'layout',
            'display_rules', 'fields'
        ]
        read_only_fields = fields


class FormSubmissionCreateSerializer(serializers.Serializer):
    """Serializer for public form submission."""

    data = serializers.DictField(child=serializers.CharField(allow_blank=True))
    gdpr_consent_given = serializers.BooleanField(default=False)
    source_url = serializers.URLField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        form = self.context.get('form')
        if not form:
            raise serializers.ValidationError("Form context is required.")

        # Validate GDPR consent if required
        if form.show_gdpr_consent and not attrs.get('gdpr_consent_given'):
            raise serializers.ValidationError({
                'gdpr_consent_given': 'GDPR consent is required.'
            })

        # Validate submission data against form fields
        from .services import FormSubmissionService
        errors = FormSubmissionService.validate_submission_data(form, attrs['data'])
        if errors:
            raise serializers.ValidationError({'data': errors})

        return attrs


class FormSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for viewing a form submission (detail)."""

    contact = serializers.SerializerMethodField()

    class Meta:
        model = FormSubmission
        fields = [
            'id', 'data', 'contact', 'ip_address',
            'gdpr_consent_given', 'source_url', 'created_at'
        ]

    def get_contact(self, obj):
        if not obj.contact:
            return None
        return {
            'id': str(obj.contact.id),
            'email': obj.contact.email,
            'first_name': obj.contact.first_name,
            'last_name': obj.contact.last_name,
        }


class FormSubmissionListSerializer(serializers.ModelSerializer):
    """Serializer for submission list view (minimal)."""

    contact_email = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = FormSubmission
        fields = [
            'id', 'contact_email', 'contact_name',
            'gdpr_consent_given', 'created_at'
        ]

    def get_contact_email(self, obj):
        if obj.contact:
            return obj.contact.email
        # Fallback: try to find email in data
        for item in (obj.data or []):
            if item.get('field_type') == 'email':
                return item.get('value', '')
        return ''

    def get_contact_name(self, obj):
        if obj.contact:
            name = f"{obj.contact.first_name} {obj.contact.last_name}".strip()
            return name or obj.contact.email
        return ''
