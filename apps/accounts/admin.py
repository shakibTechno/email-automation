"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Organization, PasswordResetToken, EmailVerificationToken, TeamInvitation, ActivityLog


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin for Organization model."""
    list_display = [
        'name', 'slug', 'plan', 'is_active',
        'max_contacts', 'created_at'
    ]
    list_filter = ['plan', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'email', 'domain']
    readonly_fields = ['id', 'slug', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'slug', 'domain', 'plan', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone')
        }),
        ('Address', {
            'fields': (
                'address_line1', 'address_line2', 'city',
                'state', 'country', 'postal_code'
            )
        }),
        ('Limits', {
            'fields': ('max_contacts', 'max_emails_per_month')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at')
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for User model."""
    list_display = [
        'email', 'first_name', 'last_name', 'organization',
        'role', 'is_active', 'is_staff', 'created_at'
    ]
    list_filter = [
        'role', 'is_active', 'is_staff', 'is_superuser',
        'is_email_verified', 'created_at'
    ]
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_login', 'date_joined']

    fieldsets = (
        (None, {
            'fields': ('id', 'email', 'password')
        }),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'phone', 'avatar')
        }),
        (_('Organization'), {
            'fields': ('organization', 'role')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'is_email_verified', 'groups', 'user_permissions'
            )
        }),
        (_('Preferences'), {
            'fields': ('timezone', 'language')
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at', 'deleted_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2', 'first_name',
                'last_name', 'organization', 'role', 'is_staff', 'is_superuser'
            ),
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin for PasswordResetToken model."""
    list_display = ['user', 'token', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used', 'expires_at', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = ['id', 'token', 'created_at', 'updated_at']


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """Admin for EmailVerificationToken model."""
    list_display = ['user', 'token', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used', 'expires_at', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = ['id', 'token', 'created_at', 'updated_at']


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    """Admin for TeamInvitation model."""
    list_display = ['email', 'organization', 'role', 'status', 'invited_by', 'expires_at', 'created_at']
    list_filter = ['status', 'role', 'created_at']
    search_fields = ['email', 'organization__name']
    readonly_fields = ['id', 'token', 'created_at', 'updated_at']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Admin for ActivityLog model."""
    list_display = ['action', 'user', 'organization', 'target_email', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__email', 'target_email', 'organization__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
