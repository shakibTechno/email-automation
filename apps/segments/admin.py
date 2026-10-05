"""
Admin configuration for the Contact Segmentation app.
"""
from django.contrib import admin
from .models import Segment, SegmentMembership


class SegmentMembershipInline(admin.TabularInline):
    """Inline for segment memberships."""
    model = SegmentMembership
    extra = 0
    readonly_fields = ['contact', 'added_by', 'created_at']
    can_delete = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    """Admin for Segment model."""
    list_display = [
        'name', 'organization', 'segment_type', 'contact_count',
        'last_calculated_at', 'created_at'
    ]
    list_filter = ['segment_type', 'organization', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'contact_count', 'last_calculated_at', 'created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        (None, {
            'fields': ('id', 'organization', 'name', 'description')
        }),
        ('Segment Configuration', {
            'fields': ('segment_type', 'rules')
        }),
        ('Statistics', {
            'fields': ('contact_count', 'last_calculated_at')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [SegmentMembershipInline]

    def get_inlines(self, request, obj):
        """Only show membership inline for static segments."""
        if obj and obj.is_static:
            return [SegmentMembershipInline]
        return []


@admin.register(SegmentMembership)
class SegmentMembershipAdmin(admin.ModelAdmin):
    """Admin for SegmentMembership model."""
    list_display = ['contact', 'segment', 'added_by', 'created_at']
    list_filter = ['segment', 'created_at']
    search_fields = ['contact__email', 'segment__name']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'contact', 'segment', 'added_by'
        )
