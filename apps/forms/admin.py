"""
Admin configuration for forms app.
"""
from django.contrib import admin
from .models import Form, FormField, FormSubmission


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 1
    fields = [
        'label', 'field_type', 'is_required', 'placeholder',
        'options', 'order', 'contact_field_mapping'
    ]
    ordering = ['order']


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    """Admin interface for Form model."""

    list_display = [
        'name', 'status', 'organization', 'form_type',
        'submission_count', 'created_at'
    ]
    list_filter = ['status', 'organization', 'form_type', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'submission_count', 'created_at', 'updated_at', 'deleted_at']
    inlines = [FormFieldInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('organization', 'name', 'description', 'status', 'form_type', 'created_by')
        }),
        ('Form Settings', {
            'fields': (
                'submit_button_text', 'success_message', 'redirect_url',
                'show_gdpr_consent', 'gdpr_consent_text'
            )
        }),
        ('Tags & Notifications', {
            'fields': ('assign_tags', 'notification_emails')
        }),
        ('Metadata', {
            'fields': ('id', 'submission_count', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    """Admin interface for FormSubmission model."""

    list_display = [
        'form', 'contact', 'ip_address',
        'gdpr_consent_given', 'created_at'
    ]
    list_filter = ['gdpr_consent_given', 'created_at']
    search_fields = ['form__name', 'contact__email']
    readonly_fields = [
        'id', 'form', 'contact', 'data', 'ip_address',
        'user_agent', 'gdpr_consent_given', 'source_url',
        'created_at', 'updated_at'
    ]
    fieldsets = (
        (None, {
            'fields': ('form', 'contact', 'data')
        }),
        ('Metadata', {
            'fields': (
                'ip_address', 'user_agent', 'gdpr_consent_given',
                'source_url', 'id', 'created_at', 'updated_at'
            ),
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50
