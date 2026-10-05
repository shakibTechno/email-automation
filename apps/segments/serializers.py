"""
Serializers for the Contact Segmentation app.
"""
from rest_framework import serializers
from apps.contacts.models import Tag
from .models import Segment, SegmentMembership
from .evaluator import FIELD_DEFINITIONS, OPERATORS_BY_TYPE, SegmentEvaluator
from .services import SegmentService


class ConditionSerializer(serializers.Serializer):
    """Serializer for a single condition within rules."""
    id = serializers.CharField(required=False)
    field = serializers.CharField()
    operator = serializers.CharField()
    value = serializers.JSONField(required=False, allow_null=True)


class RulesSerializer(serializers.Serializer):
    """Serializer for segment rules structure."""
    match_type = serializers.ChoiceField(choices=['all', 'any'], default='all')
    conditions = ConditionSerializer(many=True, required=False, default=list)
    groups = serializers.ListField(child=serializers.JSONField(), required=False, default=list)


class SegmentListSerializer(serializers.ModelSerializer):
    """Serializer for segment list view."""
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Segment
        fields = [
            'id', 'name', 'description', 'segment_type',
            'contact_count', 'last_calculated_at',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'contact_count', 'last_calculated_at', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None


class SegmentDetailSerializer(serializers.ModelSerializer):
    """Serializer for segment detail view with full rules."""
    created_by_name = serializers.SerializerMethodField()
    rules = RulesSerializer(required=False)

    class Meta:
        model = Segment
        fields = [
            'id', 'name', 'description', 'segment_type', 'rules',
            'contact_count', 'last_calculated_at',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'contact_count', 'last_calculated_at', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None


class SegmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a segment."""
    rules = RulesSerializer(required=False)

    class Meta:
        model = Segment
        fields = ['name', 'description', 'segment_type', 'rules']

    def validate(self, attrs):
        segment_type = attrs.get('segment_type', 'dynamic')
        rules = attrs.get('rules', {})

        # Dynamic segments require rules
        if segment_type == 'dynamic' and rules:
            errors = SegmentService.validate_rules(rules)
            if errors:
                raise serializers.ValidationError({'rules': errors})

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        organization = user.organization

        return SegmentService.create_segment(
            organization=organization,
            name=validated_data['name'],
            segment_type=validated_data.get('segment_type', 'dynamic'),
            description=validated_data.get('description', ''),
            rules=validated_data.get('rules', {}),
            created_by=user,
        )


class SegmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a segment."""
    rules = RulesSerializer(required=False)

    class Meta:
        model = Segment
        fields = ['name', 'description', 'rules']

    def validate_rules(self, value):
        if value and self.instance and self.instance.is_dynamic:
            errors = SegmentService.validate_rules(value)
            if errors:
                raise serializers.ValidationError(errors)
        return value

    def update(self, instance, validated_data):
        return SegmentService.update_segment(
            segment=instance,
            name=validated_data.get('name'),
            description=validated_data.get('description'),
            rules=validated_data.get('rules'),
        )


class SegmentMembershipSerializer(serializers.ModelSerializer):
    """Serializer for segment membership."""
    contact_email = serializers.CharField(source='contact.email', read_only=True)
    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = SegmentMembership
        fields = ['id', 'contact', 'contact_email', 'contact_name', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_contact_name(self, obj):
        return f"{obj.contact.first_name or ''} {obj.contact.last_name or ''}".strip()


class AddContactsSerializer(serializers.Serializer):
    """Serializer for adding contacts to a static segment."""
    contact_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=1000
    )


class RemoveContactsSerializer(serializers.Serializer):
    """Serializer for removing contacts from a static segment."""
    contact_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=1000
    )


class PreviewRulesSerializer(serializers.Serializer):
    """Serializer for previewing rules."""
    rules = RulesSerializer()
    limit = serializers.IntegerField(default=100, min_value=1, max_value=500)


class FieldDefinitionSerializer(serializers.Serializer):
    """Serializer for field definition metadata."""
    field = serializers.CharField()
    type = serializers.CharField()
    label = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField(), required=False)
    operators = serializers.ListField(child=serializers.DictField())


class SegmentContactSerializer(serializers.Serializer):
    """Serializer for contacts within a segment."""
    id = serializers.UUIDField()
    email = serializers.EmailField()
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)
    company = serializers.CharField(allow_blank=True)
    engagement_level = serializers.CharField()
    is_subscribed = serializers.BooleanField()
    lead_score = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class TagOptionSerializer(serializers.ModelSerializer):
    """Serializer for tag options in segment builder."""

    class Meta:
        model = Tag
        fields = ['id', 'name', 'color']
