"""
Serializers for the Email Campaigns app.
"""
from rest_framework import serializers
from django.db import transaction
from .models import Campaign, CampaignRecipient, ABTest, ABTestVariant
from apps.templates.models import EmailTemplate
from apps.contacts.models import Tag
from apps.contacts.serializers import TagSerializer


class ABTestVariantSerializer(serializers.ModelSerializer):
    open_rate = serializers.ReadOnlyField()
    click_rate = serializers.ReadOnlyField()
    template_name = serializers.SerializerMethodField()

    class Meta:
        model = ABTestVariant
        fields = [
            'id', 'variant', 'subject', 'sender_name', 'template', 'template_name',
            'recipient_count', 'sent_count', 'open_count', 'click_count',
            'open_rate', 'click_rate',
        ]

    def get_template_name(self, obj):
        return obj.template.name if obj.template else None


class ABTestSerializer(serializers.ModelSerializer):
    variants = ABTestVariantSerializer(many=True, read_only=True)

    class Meta:
        model = ABTest
        fields = [
            'id', 'test_type', 'test_percentage', 'winner_criteria',
            'winner_selection', 'test_duration_hours', 'winner_variant',
            'status', 'winner_sent_at', 'variants', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'winner_variant', 'status', 'winner_sent_at', 'created_at', 'updated_at']


class ABTestCreateUpdateSerializer(serializers.Serializer):
    """Used for creating or updating an AB test config (variant B values included)."""
    test_type = serializers.ChoiceField(choices=['subject', 'sender_name', 'content'])
    test_percentage = serializers.IntegerField(min_value=10, max_value=50, default=20)
    winner_criteria = serializers.ChoiceField(choices=['open_rate', 'click_rate'], default='open_rate')
    winner_selection = serializers.ChoiceField(choices=['auto', 'manual'], default='auto')
    test_duration_hours = serializers.IntegerField(min_value=1, max_value=168, default=4)

    # Variant B override — only one applies based on test_type
    variant_b_subject = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    variant_b_sender_name = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    variant_b_template = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        t = attrs['test_type']
        if t == 'subject' and not attrs.get('variant_b_subject', '').strip():
            raise serializers.ValidationError({'variant_b_subject': 'Required for subject line test.'})
        if t == 'sender_name' and not attrs.get('variant_b_sender_name', '').strip():
            raise serializers.ValidationError({'variant_b_sender_name': 'Required for sender name test.'})
        if t == 'content' and not attrs.get('variant_b_template'):
            raise serializers.ValidationError({'variant_b_template': 'Required for content test.'})
        return attrs

    def validate_variant_b_template(self, value):
        if value:
            request = self.context.get('request')
            if not EmailTemplate.objects.filter(id=value, organization=request.user.organization).exists():
                raise serializers.ValidationError("Template not found in your organization.")
        return value


class DeclareWinnerSerializer(serializers.Serializer):
    winner = serializers.ChoiceField(choices=['a', 'b'])


class CampaignListSerializer(serializers.ModelSerializer):
    """Serializer for campaign list view (minimal fields)."""

    template_name = serializers.SerializerMethodField()
    recipient_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'status', 'subject', 'sender_name',
            'sender_email', 'recipient_count', 'template_name',
            'scheduled_at', 'sent_at', 'created_at', 'updated_at'
        ]

    def get_template_name(self, obj):
        return obj.template.name if obj.template else None

    def get_recipient_count(self, obj):
        # For sent/completed campaigns, use the stored count (frozen at send time)
        if obj.status in ('sending', 'sent', 'completed'):
            return obj.recipient_count
        # For draft/scheduled, dynamically calculate from current contacts
        from .services import CampaignService
        return CampaignService.get_recipient_count(obj)


class CampaignSerializer(serializers.ModelSerializer):
    """Full serializer for Campaign model."""

    template_name = serializers.SerializerMethodField()
    template_data = serializers.SerializerMethodField()
    recipient_tags_detail = TagSerializer(
        source='recipient_tags', many=True, read_only=True
    )
    created_by_name = serializers.SerializerMethodField()
    recipient_count = serializers.SerializerMethodField()
    send_progress = serializers.SerializerMethodField()
    ab_test = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'status', 'subject', 'preheader_text',
            'sender_name', 'sender_email', 'reply_to_email',
            'template', 'template_name', 'template_data',
            'recipient_type', 'recipient_tags_detail', 'recipient_count',
            'scheduled_at', 'sent_at', 'completed_at',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
            'send_progress', 'ab_test',
        ]
        read_only_fields = [
            'id', 'status', 'recipient_count', 'sent_at',
            'completed_at', 'created_by', 'created_at', 'updated_at'
        ]

    def get_template_name(self, obj):
        return obj.template.name if obj.template else None

    def get_template_data(self, obj):
        if not obj.template:
            return None
        return {
            'id': str(obj.template.id),
            'name': obj.template.name,
            'category': obj.template.category,
            'thumbnail_url': obj.template.thumbnail_url or None,
        }

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email

    def get_recipient_count(self, obj):
        # For sent/completed campaigns, use the stored count (frozen at send time)
        if obj.status in ('sending', 'sent', 'completed'):
            return obj.recipient_count
        # For draft/scheduled, dynamically calculate from current contacts
        from .services import CampaignService
        return CampaignService.get_recipient_count(obj)

    def get_send_progress(self, obj):
        if obj.status != 'sending':
            return None
        total = obj.recipient_count or 1
        sent = CampaignRecipient.objects.filter(campaign=obj).exclude(status='pending').count()
        return {
            'sent': sent,
            'total': total,
            'percent': int(sent / total * 100),
        }

    def get_ab_test(self, obj):
        try:
            return ABTestSerializer(obj.ab_test).data
        except ABTest.DoesNotExist:
            return None


class CampaignCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a campaign."""

    recipient_tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        default=list,
    )

    class Meta:
        model = Campaign
        fields = [
            'name', 'subject', 'preheader_text',
            'sender_name', 'sender_email', 'reply_to_email',
            'template', 'recipient_type', 'recipient_tag_ids',
            'scheduled_at'
        ]

    def validate_template(self, value):
        if value:
            request = self.context.get('request')
            org = request.user.organization
            if value.organization != org:
                raise serializers.ValidationError(
                    "Template does not belong to your organization."
                )
        return value

    def validate_recipient_tag_ids(self, value):
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
    def create(self, validated_data):
        tag_ids = validated_data.pop('recipient_tag_ids', [])
        validated_data['status'] = 'draft'
        campaign = Campaign.objects.create(**validated_data)
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            campaign.recipient_tags.set(tags)
        return campaign


class CampaignUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a campaign."""

    recipient_tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Campaign
        fields = [
            'name', 'subject', 'preheader_text',
            'sender_name', 'sender_email', 'reply_to_email',
            'template', 'recipient_type', 'recipient_tag_ids',
            'scheduled_at'
        ]

    def validate(self, attrs):
        if self.instance and self.instance.status not in ('draft', 'scheduled'):
            raise serializers.ValidationError(
                "Can only edit campaigns in draft or scheduled status."
            )
        return attrs

    def validate_template(self, value):
        if value:
            request = self.context.get('request')
            org = request.user.organization
            if value.organization != org:
                raise serializers.ValidationError(
                    "Template does not belong to your organization."
                )
        return value

    def validate_recipient_tag_ids(self, value):
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
        tag_ids = validated_data.pop('recipient_tag_ids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tag_ids is not None:
            tags = Tag.objects.filter(id__in=tag_ids)
            instance.recipient_tags.set(tags)

        return instance


class CampaignSendSerializer(serializers.Serializer):
    """Serializer for send/schedule action."""

    send_now = serializers.BooleanField(default=True)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get('send_now') and not attrs.get('scheduled_at'):
            raise serializers.ValidationError(
                "Either send_now must be true or scheduled_at must be provided."
            )
        return attrs


class CampaignTestEmailSerializer(serializers.Serializer):
    """Serializer for test email action."""

    test_emails = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=5,
    )


class CampaignRecipientSerializer(serializers.ModelSerializer):
    """Serializer for campaign recipients."""

    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = CampaignRecipient
        fields = [
            'id', 'email', 'contact_name', 'status',
            'sent_at', 'opened_at', 'clicked_at'
        ]

    def get_contact_name(self, obj):
        if obj.contact:
            name = f"{obj.contact.first_name} {obj.contact.last_name}".strip()
            return name or obj.contact.email
        return obj.email
