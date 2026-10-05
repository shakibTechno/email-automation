"""
Admin configuration for CRM app.
"""
from django.contrib import admin
from .models import Pipeline, Stage, Deal, DealContact, Activity, DealStageHistory


class StageInline(admin.TabularInline):
    model = Stage
    extra = 0
    ordering = ['position']


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'is_default', 'total_deals', 'total_value', 'created_at']
    list_filter = ['organization', 'is_default', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    inlines = [StageInline]
    fieldsets = (
        (None, {
            'fields': ('organization', 'name', 'description', 'is_default', 'created_by')
        }),
        ('Stats', {
            'fields': ('total_deals', 'total_value')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ['name', 'pipeline', 'position', 'stage_type', 'default_probability', 'color']
    list_filter = ['stage_type', 'pipeline']
    search_fields = ['name', 'pipeline__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['pipeline', 'position']
    list_per_page = 50


class DealContactInline(admin.TabularInline):
    model = DealContact
    extra = 0


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'status', 'pipeline', 'stage', 'value', 'priority',
        'probability', 'weighted_value', 'assigned_to', 'close_date', 'created_at'
    ]
    list_filter = ['status', 'priority', 'pipeline', 'organization', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'weighted_value', 'created_at', 'updated_at', 'deleted_at']
    inlines = [DealContactInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('organization', 'title', 'description', 'status', 'priority')
        }),
        ('Pipeline', {
            'fields': ('pipeline', 'stage', 'position')
        }),
        ('Financial', {
            'fields': ('value', 'currency', 'probability', 'weighted_value')
        }),
        ('Dates', {
            'fields': ('close_date', 'closed_at')
        }),
        ('Win/Loss', {
            'fields': ('win_reason', 'loss_reason')
        }),
        ('People', {
            'fields': ('primary_contact', 'created_by', 'assigned_to')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50


@admin.register(DealContact)
class DealContactAdmin(admin.ModelAdmin):
    list_display = ['deal', 'contact', 'role', 'is_primary', 'created_at']
    list_filter = ['role', 'is_primary']
    search_fields = ['deal__title', 'contact__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_per_page = 50


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'activity_type', 'deal', 'contact',
        'is_completed', 'due_date', 'assigned_to', 'created_at'
    ]
    list_filter = ['activity_type', 'is_completed', 'organization', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('organization', 'activity_type', 'title', 'description')
        }),
        ('Links', {
            'fields': ('deal', 'contact')
        }),
        ('Schedule', {
            'fields': ('due_date', 'duration', 'is_completed', 'completed_at')
        }),
        ('People', {
            'fields': ('created_by', 'assigned_to')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50


@admin.register(DealStageHistory)
class DealStageHistoryAdmin(admin.ModelAdmin):
    list_display = ['deal', 'from_stage', 'to_stage', 'moved_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['deal__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 50
