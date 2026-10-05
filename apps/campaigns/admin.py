"""
Admin configuration for campaigns app.
"""
from django.contrib import admin
from .models import Campaign, CampaignRecipient


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Admin interface for Campaign model."""

    list_display = [
        'name', 'status', 'organization', 'subject',
        'recipient_count', 'scheduled_at', 'sent_at', 'created_at'
    ]
    list_filter = ['status', 'organization', 'recipient_type', 'created_at']
    search_fields = ['name', 'subject']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('organization', 'name', 'status', 'created_by')
        }),
        ('Email Content', {
            'fields': ('template', 'subject', 'preheader_text')
        }),
        ('Sender', {
            'fields': ('sender_name', 'sender_email', 'reply_to_email')
        }),
        ('Recipients', {
            'fields': ('recipient_type', 'recipient_tags', 'recipient_count')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'sent_at', 'completed_at')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    """Admin interface for CampaignRecipient model."""

    list_display = [
        'campaign', 'email', 'status',
        'sent_at', 'opened_at', 'clicked_at', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['email', 'campaign__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('campaign', 'contact', 'email', 'status')
        }),
        ('Tracking', {
            'fields': ('sent_at', 'opened_at', 'clicked_at', 'bounced_at')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50
