"""
Serializers for the Landing Pages app.
"""
from rest_framework import serializers
from django.db import transaction
from django.conf import settings

from .domains import normalize_domain, reserved_domain_error
from .models import (
    LandingDomain,
    LandingPage,
    LandingPageTemplate,
    LandingPageAsset,
    PageView,
)


class LandingDomainSerializer(serializers.ModelSerializer):
    """A connected domain as the settings page renders it."""

    dns_records = serializers.ListField(read_only=True)
    conflicts_with_email = serializers.BooleanField(
        source='conflicting_sending_domain', read_only=True,
    )
    verification_url = serializers.CharField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    page_count = serializers.SerializerMethodField()

    class Meta:
        model = LandingDomain
        fields = [
            'id', 'domain', 'status', 'is_verified', 'is_primary',
            'dns_records', 'conflicts_with_email', 'verification_url',
            'verified_at', 'last_check_at', 'last_check_error', 'last_seen_at',
            'page_count', 'created_at',
        ]
        # Status is reached through `verify`, never written: a domain must not
        # be able to declare itself verified.
        read_only_fields = [
            'id', 'status', 'is_primary', 'verified_at', 'last_check_at',
            'last_check_error', 'last_seen_at', 'created_at',
        ]

    def get_page_count(self, obj):
        return getattr(obj, 'page_count', None) or obj.pages.count()

    def validate_domain(self, value):
        value = normalize_domain(value)
        error = reserved_domain_error(value)
        if error:
            raise serializers.ValidationError(error)
        return value


class LandingPageListSerializer(serializers.ModelSerializer):
    """Serializer for landing page list view (minimal fields)."""

    public_url = serializers.CharField(read_only=True)
    conversion_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = LandingPage
        fields = [
            'id', 'name', 'slug', 'status',
            'view_count', 'conversion_count', 'conversion_rate',
            'public_url', 'published_at', 'created_at', 'updated_at'
        ]


class LandingPageSerializer(serializers.ModelSerializer):
    """Full serializer for LandingPage model."""

    created_by_name = serializers.SerializerMethodField()
    public_url = serializers.CharField(read_only=True)
    conversion_rate = serializers.FloatField(read_only=True)
    form_name = serializers.SerializerMethodField()
    domain_name = serializers.CharField(source='domain.domain', read_only=True, default=None)
    # Both addresses: the UI shows where a page is served from and
    # where it can always be reached, which differ while a domain is
    # still verifying.
    platform_url = serializers.CharField(read_only=True)

    class Meta:
        model = LandingPage
        fields = [
            'id', 'name', 'slug', 'status',
            'html_content', 'design_json', 'css_content',
            'seo_title', 'seo_description', 'seo_keywords', 'og_image',
            'favicon', 'google_analytics_id', 'facebook_pixel_id',
            'custom_head_code', 'custom_body_code',
            'form', 'form_name',
            'domain', 'domain_name', 'is_domain_home',
            'view_count', 'conversion_count', 'conversion_rate',
            'public_url', 'platform_url', 'published_at',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'view_count', 'conversion_count', 'created_by',
            'published_at', 'created_at', 'updated_at'
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email

    def get_form_name(self, obj):
        if obj.form:
            return obj.form.name
        return None


class LandingPageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a landing page."""

    template_id = serializers.UUIDField(required=False, write_only=True, allow_null=True)
    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = LandingPage
        fields = ['name', 'slug', 'template_id']

    def validate_slug(self, value):
        if value:
            request = self.context.get('request')
            org = request.user.organization
            if LandingPage.objects.filter(organization=org, slug=value).exists():
                raise serializers.ValidationError("A landing page with this slug already exists.")
        return value

    def validate_template_id(self, value):
        if value:
            from .models import LandingPageTemplate
            try:
                template = LandingPageTemplate.objects.get(id=value, is_active=True)
                # Must be system template or belong to user's org
                request = self.context.get('request')
                if not template.is_system and template.organization != request.user.organization:
                    raise serializers.ValidationError("Template not found.")
            except LandingPageTemplate.DoesNotExist:
                raise serializers.ValidationError("Template not found.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        template_id = validated_data.pop('template_id', None)
        request = self.context.get('request')

        if template_id:
            from .services import LandingPageTemplateService
            template = LandingPageTemplate.objects.get(id=template_id)
            return LandingPageTemplateService.create_from_template(
                template=template,
                organization=request.user.organization,
                user=request.user,
                name=validated_data.get('name'),
                slug=validated_data.get('slug', '')
            )
        else:
            return LandingPage.objects.create(
                organization=request.user.organization,
                created_by=request.user,
                **validated_data
            )


class LandingPageUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a landing page."""

    form_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = LandingPage
        fields = [
            'name', 'slug',
            'html_content', 'design_json', 'css_content',
            'seo_title', 'seo_description', 'seo_keywords', 'og_image',
            'favicon', 'google_analytics_id', 'facebook_pixel_id',
            'custom_head_code', 'custom_body_code',
            'domain', 'is_domain_home',
            'form_id'
        ]

    def validate_slug(self, value):
        if value:
            request = self.context.get('request')
            org = request.user.organization
            instance = self.instance
            if LandingPage.objects.filter(
                organization=org, slug=value
            ).exclude(pk=instance.pk).exists():
                raise serializers.ValidationError("A landing page with this slug already exists.")
        return value

    def validate_domain(self, value):
        """A page may only be pinned to one of its own organization's domains."""
        if value is None:
            return value
        request = self.context.get('request')
        if value.organization_id != request.user.organization_id:
            # Phrased as not-found rather than not-yours: the ids of
            # other tenants' domains are not something to confirm.
            raise serializers.ValidationError('Domain not found.')
        return value

    def validate(self, attrs):
        """At most one page per domain may sit at its root."""
        if not attrs.get('is_domain_home'):
            return attrs
        instance = self.instance
        domain = attrs.get('domain', getattr(instance, 'domain', None))
        clash = LandingPage.objects.filter(
            organization_id=instance.organization_id,
            is_domain_home=True,
            domain=domain,
        ).exclude(pk=instance.pk)
        if clash.exists():
            raise serializers.ValidationError({
                'is_domain_home': (
                    f'"{clash.first().name}" is already the home page for this domain.'
                )
            })
        return attrs

    def validate_form_id(self, value):
        if value:
            from apps.forms.models import Form
            request = self.context.get('request')
            try:
                Form.objects.get(id=value, organization=request.user.organization)
            except Form.DoesNotExist:
                raise serializers.ValidationError("Form not found.")
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        form_id = validated_data.pop('form_id', None)

        if form_id is not None:
            if form_id:
                from apps.forms.models import Form
                instance.form = Form.objects.get(id=form_id)
            else:
                instance.form = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class LandingPageDesignSerializer(serializers.ModelSerializer):
    """Serializer for saving GrapesJS design (auto-save)."""

    class Meta:
        model = LandingPage
        fields = ['html_content', 'design_json', 'css_content']


class PublicLandingPageSerializer(serializers.ModelSerializer):
    """Serializer for public landing page rendering."""

    public_url = serializers.CharField(read_only=True)

    class Meta:
        model = LandingPage
        fields = [
            'id', 'name', 'slug',
            'html_content', 'css_content',
            'seo_title', 'seo_description', 'og_image',
            'favicon', 'google_analytics_id', 'facebook_pixel_id',
            'custom_head_code', 'custom_body_code',
            'public_url'
        ]
        read_only_fields = fields


class LandingPageTemplateSerializer(serializers.ModelSerializer):
    """Serializer for template list view."""

    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = LandingPageTemplate
        fields = [
            'id', 'name', 'description', 'category', 'category_display',
            'thumbnail', 'is_system', 'usage_count', 'created_at'
        ]


class LandingPageTemplateDetailSerializer(serializers.ModelSerializer):
    """Serializer for template detail with design data."""

    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = LandingPageTemplate
        fields = [
            'id', 'name', 'description', 'category', 'category_display',
            'thumbnail', 'html_content', 'design_json', 'css_content',
            'is_system', 'usage_count', 'created_at'
        ]


class SaveAsTemplateSerializer(serializers.Serializer):
    """Serializer for saving a landing page as a template."""

    landing_page_id = serializers.UUIDField()
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    category = serializers.ChoiceField(choices=LandingPageTemplate.CATEGORY_CHOICES)

    def validate_landing_page_id(self, value):
        request = self.context.get('request')
        try:
            LandingPage.objects.get(
                id=value,
                organization=request.user.organization
            )
        except LandingPage.DoesNotExist:
            raise serializers.ValidationError("Landing page not found.")
        return value


class LandingPageAssetSerializer(serializers.ModelSerializer):
    """Serializer for landing page assets."""

    url = serializers.CharField(read_only=True)

    class Meta:
        model = LandingPageAsset
        fields = [
            'id', 'file', 'file_type', 'file_name',
            'file_size', 'mime_type', 'url', 'created_at'
        ]
        read_only_fields = ['id', 'file_type', 'file_name', 'file_size', 'mime_type', 'url', 'created_at']


class PageAnalyticsSerializer(serializers.Serializer):
    """Serializer for page analytics data."""

    total_views = serializers.IntegerField()
    unique_views = serializers.IntegerField()
    conversion_count = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    views_by_date = serializers.ListField(
        child=serializers.DictField()
    )
