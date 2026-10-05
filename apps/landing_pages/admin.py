"""
Admin configuration for the Landing Pages app.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import LandingPage, LandingPageTemplate, LandingPageAsset, PageView


class LandingPageAssetInline(admin.TabularInline):
    model = LandingPageAsset
    extra = 0
    readonly_fields = ['file_type', 'file_name', 'file_size', 'mime_type', 'created_at']
    fields = ['file', 'file_type', 'file_name', 'file_size', 'created_at']


@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'slug', 'organization', 'status',
        'view_count', 'conversion_count', 'published_at', 'created_at'
    ]
    list_filter = ['status', 'organization', 'created_at']
    search_fields = ['name', 'slug', 'seo_title']
    readonly_fields = [
        'id', 'view_count', 'conversion_count',
        'published_at', 'created_at', 'updated_at', 'deleted_at',
        'public_url_display'
    ]
    raw_id_fields = ['organization', 'created_by', 'form']
    inlines = [LandingPageAssetInline]

    fieldsets = (
        (None, {
            'fields': ('id', 'organization', 'name', 'slug', 'status', 'public_url_display')
        }),
        ('Content', {
            'fields': ('html_content', 'design_json', 'css_content'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('seo_title', 'seo_description', 'seo_keywords', 'og_image', 'favicon')
        }),
        ('Analytics Integration', {
            'fields': ('google_analytics_id', 'facebook_pixel_id')
        }),
        ('Custom Code', {
            'fields': ('custom_head_code', 'custom_body_code'),
            'classes': ('collapse',)
        }),
        ('Form', {
            'fields': ('form',)
        }),
        ('Statistics', {
            'fields': ('view_count', 'conversion_count')
        }),
        ('Metadata', {
            'fields': ('created_by', 'published_at', 'created_at', 'updated_at', 'deleted_at')
        }),
    )

    def public_url_display(self, obj):
        if obj.public_url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.public_url, obj.public_url)
        return '-'
    public_url_display.short_description = 'Public URL'


@admin.register(LandingPageTemplate)
class LandingPageTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'is_system', 'is_active',
        'usage_count', 'organization', 'created_at'
    ]
    list_filter = ['category', 'is_system', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'usage_count', 'created_at', 'updated_at']
    raw_id_fields = ['organization']

    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'description', 'category', 'thumbnail')
        }),
        ('Content', {
            'fields': ('html_content', 'design_json', 'css_content'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('organization', 'is_system', 'is_active', 'usage_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(LandingPageAsset)
class LandingPageAssetAdmin(admin.ModelAdmin):
    list_display = [
        'file_name', 'file_type', 'landing_page',
        'organization', 'file_size', 'created_at'
    ]
    list_filter = ['file_type', 'organization', 'created_at']
    search_fields = ['file_name']
    readonly_fields = ['id', 'file_type', 'file_size', 'mime_type', 'created_at', 'updated_at']
    raw_id_fields = ['organization', 'landing_page']


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = [
        'landing_page', 'ip_address', 'is_unique',
        'referrer', 'created_at'
    ]
    list_filter = ['is_unique', 'created_at']
    search_fields = ['landing_page__name', 'ip_address', 'referrer']
    readonly_fields = ['id', 'landing_page', 'ip_address', 'user_agent', 'referrer', 'session_id', 'is_unique', 'created_at']
    raw_id_fields = ['landing_page']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
