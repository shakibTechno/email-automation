"""
Admin configuration for templates app.
"""
from django.contrib import admin
from .models import EmailTemplate, TemplateImage


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """Admin interface for EmailTemplate model."""

    list_display = [
        'name', 'category', 'organization',
        'is_preset', 'is_active', 'created_at'
    ]
    list_filter = ['category', 'is_preset', 'is_active', 'organization', 'created_at']
    search_fields = ['name', 'description', 'subject']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('organization', 'name', 'description', 'category', 'subject')
        }),
        ('Design', {
            'fields': ('design_json', 'html_content', 'thumbnail_url'),
            'classes': ('collapse',)
        }),
        ('Flags', {
            'fields': ('is_preset', 'is_active')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50


@admin.register(TemplateImage)
class TemplateImageAdmin(admin.ModelAdmin):
    """Admin interface for TemplateImage model."""

    list_display = [
        'original_filename', 'organization', 'file_size',
        'width', 'height', 'created_at'
    ]
    list_filter = ['organization', 'created_at']
    search_fields = ['original_filename']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('organization', 'image', 'original_filename')
        }),
        ('File Info', {
            'fields': ('file_size', 'width', 'height')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50
