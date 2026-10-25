"""
Serializers for the Contact app.
"""
from rest_framework import serializers
from django.db import transaction
from .models import Contact, Tag, ContactTag, CustomField
from . import fields as contact_fields
from .custom_fields import CustomFieldError, CustomFieldService


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model."""

    # A tag is only meaningful through what it is applied to, so the usage
    # count travels with the tag rather than costing the client one request
    # per row to discover it. The list comes from TagViewSet's annotation;
    # create/update responses serialize a saved instance that carries no
    # annotation, hence the fallback.
    contact_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'color', 'description', 'contact_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'contact_count', 'created_at', 'updated_at']

    def get_contact_count(self, obj) -> int:
        annotated = getattr(obj, 'contact_count', None)
        return annotated if annotated is not None else obj.contact_tags.count()


class CustomFieldSerializer(serializers.ModelSerializer):
    """Serializer for CustomField model."""

    contact_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomField
        fields = [
            'id', 'key', 'name', 'field_type', 'is_required',
            'default_value', 'dropdown_options', 'help_text',
            'display_order', 'contact_count',
            'created_at', 'updated_at'
        ]
        # `key` is read-only on purpose. It is what values are stored under, so
        # changing it would orphan every value already saved — which is the
        # exact failure the key/name split exists to prevent. Rename the label
        # instead; that is free.
        read_only_fields = ['id', 'key', 'contact_count', 'created_at', 'updated_at']

    def get_contact_count(self, obj):
        """
        How many contacts hold a value for this field.

        Shown when deleting one, because "remove this field" reads very
        differently at 0 contacts and at 4,000.
        """
        from .models import Contact

        if not obj.key:
            return 0
        return Contact.objects.filter(
            organization_id=obj.organization_id,
            custom_fields__has_key=obj.key,
        ).count()

    def validate_dropdown_options(self, value):
        """A list of choices is required for the types that choose from one."""
        field_type = self.initial_data.get('field_type') or getattr(
            self.instance, 'field_type', None
        )
        if field_type in ('dropdown', 'multiselect'):
            if not isinstance(value, list):
                raise serializers.ValidationError(
                    'Provide the choices as a list for this field type.'
                )
            cleaned = [str(v).strip() for v in value if str(v).strip()]
            if len(set(cleaned)) != len(cleaned):
                raise serializers.ValidationError('Choices must be unique.')
            return cleaned
        return value

    def validate_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Give the field a name.')
        from django.utils.text import slugify

        if not slugify(value):
            raise serializers.ValidationError(
                'The name needs at least one letter or number.'
            )
        return value


class CustomFieldsValidationMixin:
    """
    Validates `custom_fields` against the organization's definitions.

    A mixin because three serializers accept the field — full, create and
    update — and only one of them having the check is how a create slipped
    past it: the API create path uses ContactCreateSerializer, so an
    undeclared key was still accepted there while the full serializer
    rejected it.
    """

    def validate_custom_fields(self, value):
        request = self.context.get('request')
        organization = getattr(getattr(request, 'user', None), 'organization', None)
        try:
            return CustomFieldService.validate_and_coerce(
                organization, value,
                # An update that sets one field must not fail because a
                # different required one was not in this payload.
                partial=self.instance is not None,
            )
        except CustomFieldError as exc:
            raise serializers.ValidationError(exc.errors)

class ContactListSerializer(serializers.ModelSerializer):
    """Serializer for Contact list view (minimal fields)."""

    full_name = serializers.CharField(read_only=True)
    tags = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'company', 'phone', 'is_subscribed', 'engagement_level',
            'lead_score', 'tags', 'assigned_to', 'assigned_to_name',
            'created_at', 'last_activity_at'
        ]

    def get_tags(self, obj):
        contact_tags = obj.contact_tags.select_related('tag').all()
        return TagSerializer([ct.tag for ct in contact_tags], many=True).data

    def get_assigned_to_name(self, obj):
        if obj.assigned_to_id:
            u = obj.assigned_to
            return u.full_name or u.email
        return None


class ContactSerializer(CustomFieldsValidationMixin, serializers.ModelSerializer):
    """Full serializer for Contact model."""

    full_name = serializers.CharField(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False,
        write_only=True
    )
    tag_details = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'company', 'job_title',
            'lead_score', 'engagement_level',
            'is_subscribed', 'is_verified',
            'unsubscribed_at', 'bounced_at',
            'salutation', 'middle_name', 'preferred_name', 'date_of_birth',
            'mobile_phone', 'website', 'linkedin_url',
            'address_line1', 'address_line2', 'city', 'region',
            'postal_code', 'country', 'timezone', 'locale',
            'lifecycle_stage', 'status', 'bounce_type', 'complained_at',
            'consent_at', 'consent_source', 'opt_in_ip', 'double_opt_in_at',
            'external_id',
            'custom_fields', 'source', 'last_activity_at',
            'assigned_to', 'assigned_to_name',
            'tags', 'tag_details',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'full_name', 'tag_details', 'assigned_to_name',
            'created_at', 'updated_at',
            # Derived by Contact.save() or owned by the delivery pipeline.
            # Writable here would be a second way to set the same fact.
            'status', 'bounce_type', 'complained_at',
        ]

    def get_tag_details(self, obj):
        contact_tags = obj.contact_tags.select_related('tag').all()
        return TagSerializer([ct.tag for ct in contact_tags], many=True).data

    def get_assigned_to_name(self, obj):
        if obj.assigned_to_id:
            u = obj.assigned_to
            return u.full_name or u.email
        return None

    def validate_email(self, value):
        """Validate email uniqueness within organization."""
        request = self.context.get('request')
        organization = request.user.organization

        # Check for existing contact with same email in organization
        queryset = Contact.objects.filter(
            organization=organization,
            email=value
        )

        # Exclude current instance if updating
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A contact with this email already exists in your organization."
            )

        return value

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        # organization is passed via perform_create in the view
        contact = Contact.objects.create(**validated_data)

        # Add tags
        for tag in tags:
            ContactTag.objects.create(contact=contact, tag=tag)

        return contact

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)

        # Update contact fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tags if provided
        if tags is not None:
            # Remove existing tags
            ContactTag.objects.filter(contact=instance).delete()
            # Add new tags
            for tag in tags:
                ContactTag.objects.create(contact=instance, tag=tag)

        return instance


class ContactCreateSerializer(CustomFieldsValidationMixin, serializers.ModelSerializer):
    """Serializer for creating a contact."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Contact
        fields = [
            'email', 'first_name', 'last_name',
            'phone', 'company', 'job_title',
            'lead_score', 'engagement_level',
            'salutation', 'middle_name', 'preferred_name', 'date_of_birth',
            'mobile_phone', 'website', 'linkedin_url',
            'address_line1', 'address_line2', 'city', 'region',
            'postal_code', 'country', 'timezone', 'locale',
            'lifecycle_stage',
            'consent_at', 'consent_source', 'opt_in_ip', 'double_opt_in_at',
            'external_id',
            'is_subscribed', 'custom_fields',
            'source', 'tags', 'assigned_to'
        ]

    def validate_email(self, value):
        """Validate email uniqueness within organization."""
        request = self.context.get('request')
        organization = request.user.organization

        if Contact.objects.filter(organization=organization, email=value).exists():
            raise serializers.ValidationError(
                "A contact with this email already exists in your organization."
            )

        return value

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        # organization is passed via perform_create in the view
        contact = Contact.objects.create(**validated_data)

        # Add tags
        for tag in tags:
            ContactTag.objects.create(contact=contact, tag=tag)

        return contact


class ContactUpdateSerializer(CustomFieldsValidationMixin, serializers.ModelSerializer):
    """Serializer for updating a contact."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Contact
        fields = [
            'email', 'first_name', 'last_name',
            'phone', 'company', 'job_title',
            'lead_score', 'engagement_level',
            'salutation', 'middle_name', 'preferred_name', 'date_of_birth',
            'mobile_phone', 'website', 'linkedin_url',
            'address_line1', 'address_line2', 'city', 'region',
            'postal_code', 'country', 'timezone', 'locale',
            'lifecycle_stage',
            'consent_at', 'consent_source', 'opt_in_ip', 'double_opt_in_at',
            'external_id',
            'is_subscribed', 'custom_fields',
            'tags', 'assigned_to'
        ]

    def validate_email(self, value):
        """Validate email uniqueness within organization."""
        request = self.context.get('request')
        organization = request.user.organization

        queryset = Contact.objects.filter(organization=organization, email=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A contact with this email already exists in your organization."
            )

        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)

        # Update contact fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tags if provided
        if tags is not None:
            ContactTag.objects.filter(contact=instance).delete()
            for tag in tags:
                ContactTag.objects.create(contact=instance, tag=tag)

        return instance


class BulkDeleteSerializer(serializers.Serializer):
    """Serializer for bulk delete operation."""

    contact_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )

    def validate_contact_ids(self, value):
        """Validate that contacts exist and belong to user's organization."""
        request = self.context.get('request')
        organization = request.user.organization

        contacts = Contact.objects.filter(
            id__in=value,
            organization=organization
        )

        if contacts.count() != len(value):
            raise serializers.ValidationError(
                "Some contacts do not exist or do not belong to your organization."
            )

        return value


class BulkTagSerializer(serializers.Serializer):
    """Serializer for bulk tag operation."""

    contact_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
    action = serializers.ChoiceField(choices=['add', 'remove'])

    def validate_contact_ids(self, value):
        """Validate that contacts exist and belong to user's organization."""
        request = self.context.get('request')
        organization = request.user.organization

        contacts = Contact.objects.filter(
            id__in=value,
            organization=organization
        )

        if contacts.count() != len(value):
            raise serializers.ValidationError(
                "Some contacts do not exist or do not belong to your organization."
            )

        return value

    def validate_tag_ids(self, value):
        """Validate that tags exist and belong to user's organization."""
        request = self.context.get('request')
        organization = request.user.organization

        tags = Tag.objects.filter(
            id__in=value,
            organization=organization
        )

        if tags.count() != len(value):
            raise serializers.ValidationError(
                "Some tags do not exist or do not belong to your organization."
            )

        return value


class ContactImportSerializer(serializers.Serializer):
    """Serializer for CSV import."""

    file = serializers.FileField()
    field_mapping = serializers.JSONField(required=False)
    skip_duplicates = serializers.BooleanField(default=True)
    update_existing = serializers.BooleanField(default=False)

    def validate_field_mapping(self, value):
        """
        Check every mapping target before the importer touches the model.

        This is the gate that was missing. The importer assigned to whatever
        attribute name this dictionary named, so {"col": "organization_id"}
        wrote contacts into another tenant's organization, and "id",
        "deleted_at" and "lead_score" were equally reachable. The targets the
        UI offers were always safe; nothing stopped a hand-made request.
        """
        if value in (None, ''):
            return value
        if not isinstance(value, dict):
            raise serializers.ValidationError('field_mapping must be an object.')

        errors = {}
        for column, target in value.items():
            if target in (None, ''):
                continue  # a deliberately skipped column
            reason = contact_fields.rejection_reason(target, contact_fields.IMPORT)
            if reason:
                errors[str(column)] = reason
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate_file(self, value):
        """Validate that the file is a CSV."""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("File must be a CSV file.")

        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size must be less than 5MB.")

        return value
