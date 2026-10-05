"""
Admin configuration for contacts app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Contact, Tag, ContactTag, CustomField


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Admin interface for Contact model."""

    list_display = [
        'email', 'full_name', 'company', 'organization',
        'is_subscribed', 'engagement_level', 'lead_score',
        'created_at'
    ]
    list_filter = [
        'is_subscribed', 'is_verified', 'engagement_level',
        'source', 'created_at', 'organization'
    ]
    search_fields = [
        'email', 'first_name', 'last_name', 'company', 'phone'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'deleted_at',
        'unsubscribed_at', 'bounced_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'organization', 'email', 'first_name', 'last_name',
                'phone', 'company', 'job_title'
            )
        }),
        ('Engagement', {
            'fields': ('lead_score', 'engagement_level')
        }),
        ('Status', {
            'fields': (
                'is_subscribed', 'is_verified',
                'unsubscribed_at', 'bounced_at'
            )
        }),
        ('Custom Fields', {
            'fields': ('custom_fields',)
        }),
        ('Tracking', {
            'fields': ('source', 'last_activity_at')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50
    actions = ['mark_as_subscribed', 'mark_as_unsubscribed', 'soft_delete_contacts']

    def mark_as_subscribed(self, request, queryset):
        """Action to subscribe contacts."""
        count = 0
        for contact in queryset:
            contact.resubscribe()
            count += 1
        self.message_user(request, f'{count} contacts subscribed.')
    mark_as_subscribed.short_description = 'Mark as subscribed'

    def mark_as_unsubscribed(self, request, queryset):
        """Action to unsubscribe contacts."""
        count = 0
        for contact in queryset:
            contact.unsubscribe()
            count += 1
        self.message_user(request, f'{count} contacts unsubscribed.')
    mark_as_unsubscribed.short_description = 'Mark as unsubscribed'

    def soft_delete_contacts(self, request, queryset):
        """Action to soft delete contacts."""
        count = 0
        for contact in queryset:
            contact.soft_delete()
            count += 1
        self.message_user(request, f'{count} contacts deleted.')
    soft_delete_contacts.short_description = 'Soft delete selected contacts'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin interface for Tag model."""

    list_display = ['name', 'color_badge', 'organization', 'created_at']
    list_filter = ['color', 'organization', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('organization', 'name', 'color', 'description')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['name']
    list_per_page = 50

    def color_badge(self, obj):
        """Display color as a badge."""
        color_map = {
            'red': '#dc3545',
            'blue': '#007bff',
            'green': '#28a745',
            'yellow': '#ffc107',
            'purple': '#6f42c1',
            'orange': '#fd7e14',
            'pink': '#e83e8c',
            'gray': '#6c757d',
        }
        color_hex = color_map.get(obj.color, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color_hex,
            obj.color
        )
    color_badge.short_description = 'Color'


@admin.register(ContactTag)
class ContactTagAdmin(admin.ModelAdmin):
    """Admin interface for ContactTag model."""

    list_display = ['contact', 'tag', 'created_at']
    list_filter = ['tag', 'created_at']
    search_fields = ['contact__email', 'tag__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 50


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    """Admin interface for CustomField model."""

    list_display = [
        'name', 'field_type', 'organization',
        'is_required', 'created_at'
    ]
    list_filter = ['field_type', 'is_required', 'organization', 'created_at']
    search_fields = ['name', 'help_text']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': (
                'organization', 'name', 'field_type',
                'is_required', 'default_value'
            )
        }),
        ('Dropdown Options', {
            'fields': ('dropdown_options',),
            'classes': ('collapse',)
        }),
        ('Help', {
            'fields': ('help_text',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['name']
    list_per_page = 50
