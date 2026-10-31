from django.db import transaction
from django.db.models import F, Q
from rest_framework import serializers

from .models import (
    Popup, PopupTemplate, default_design, default_frequency, default_targeting,
    default_triggers,
)


class PopupListSerializer(serializers.ModelSerializer):
    conversion_rate = serializers.FloatField(read_only=True)
    form_name = serializers.CharField(source='form.name', read_only=True, default=None)
    is_live = serializers.SerializerMethodField()

    class Meta:
        model = Popup
        fields = [
            'id', 'name', 'popup_type', 'status', 'title',
            'form', 'form_name',
            'starts_at', 'ends_at', 'is_live',
            'impression_count', 'click_count', 'conversion_count',
            'conversion_rate', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_is_live(self, obj):
        """Status alone does not say it: a schedule can hold it back."""
        return obj.is_live()


class PopupSerializer(serializers.ModelSerializer):
    conversion_rate = serializers.FloatField(read_only=True)
    form_name = serializers.CharField(source='form.name', read_only=True, default=None)
    is_live = serializers.SerializerMethodField()

    class Meta:
        model = Popup
        fields = [
            'id', 'name', 'popup_type', 'status',
            'title', 'description', 'image_url', 'image_alt',
            'cta_text', 'cta_url', 'secondary_cta_text', 'secondary_cta_url',
            'form', 'form_name',
            'design', 'triggers', 'targeting', 'frequency',
            'starts_at', 'ends_at', 'is_live',
            'impression_count', 'click_count', 'conversion_count',
            'conversion_rate', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'form_name', 'is_live', 'impression_count', 'click_count',
            'conversion_count', 'conversion_rate', 'created_by',
            'created_at', 'updated_at',
        ]

    def get_is_live(self, obj):
        return obj.is_live()

    def validate_form(self, value):
        """A popup may only embed a form from its own organization."""
        if value is None:
            return value
        organization = self.context['request'].user.organization
        if value.organization_id != organization.id:
            raise serializers.ValidationError('That form belongs to another account.')
        return value

    def validate(self, attrs):
        starts = attrs.get('starts_at', getattr(self.instance, 'starts_at', None))
        ends = attrs.get('ends_at', getattr(self.instance, 'ends_at', None))
        if starts and ends and ends <= starts:
            raise serializers.ValidationError({
                'ends_at': 'The end must come after the start.',
            })

        # A popup with neither a form nor a call to action shows the visitor
        # something they cannot act on, which is worse than not showing it.
        status = attrs.get('status', getattr(self.instance, 'status', Popup.STATUS_DRAFT))
        if status != Popup.STATUS_DRAFT:
            form = attrs.get('form', getattr(self.instance, 'form', None))
            cta = attrs.get('cta_text', getattr(self.instance, 'cta_text', ''))
            if not form and not cta:
                raise serializers.ValidationError({
                    'cta_text': (
                        'Add a form or a call to action before publishing — '
                        'otherwise there is nothing for a visitor to do.'
                    ),
                })
        return attrs


class PopupCreateSerializer(PopupSerializer):
    """Create, optionally from a template."""
    template_id = serializers.UUIDField(
        required=False, write_only=True, allow_null=True,
    )

    class Meta(PopupSerializer.Meta):
        fields = PopupSerializer.Meta.fields + ['template_id']

    def validate_template_id(self, value):
        if value is None:
            return value
        organization = self.context['request'].user.organization
        exists = (
            PopupTemplate.objects
            .filter(id=value, is_active=True)
            .filter(Q(is_system=True) | Q(organization=organization))
            .exists()
        )
        if not exists:
            raise serializers.ValidationError('Unknown template.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        template_id = validated_data.pop('template_id', None)
        if not template_id:
            return super().create(validated_data)

        template = PopupTemplate.objects.get(id=template_id)
        content = template.content or {}
        # The template supplies what the marketer has not. Anything they typed
        # on the way in wins -- they have seen their version, not ours.
        for field in (
            'title', 'description', 'image_url', 'image_alt',
            'cta_text', 'cta_url', 'secondary_cta_text', 'secondary_cta_url',
        ):
            validated_data.setdefault(field, content.get(field, ''))
        validated_data.setdefault('popup_type', template.popup_type)
        validated_data.setdefault('design', template.design or default_design())
        validated_data.setdefault('triggers', template.triggers or default_triggers())
        validated_data.setdefault('targeting', default_targeting())
        validated_data.setdefault('frequency', default_frequency())

        popup = super().create(validated_data)
        PopupTemplate.objects.filter(pk=template.pk).update(
            usage_count=F('usage_count') + 1
        )
        return popup


class PopupTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopupTemplate
        fields = [
            'id', 'name', 'description', 'category', 'popup_type',
            'content', 'design', 'triggers', 'wants_form',
            'is_system', 'usage_count',
        ]
        read_only_fields = fields


class PopupStatusSerializer(serializers.Serializer):
    """The one field the pause/publish actions change."""
    status = serializers.ChoiceField(choices=Popup.STATUS_CHOICES)
