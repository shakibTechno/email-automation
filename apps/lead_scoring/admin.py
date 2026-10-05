from django.contrib import admin
from .models import ScoringRule, ScoreHistory, ScoreThreshold


@admin.register(ScoringRule)
class ScoringRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'rule_type', 'points', 'is_active', 'priority', 'event_type']
    list_filter = ['rule_type', 'is_active', 'event_type', 'organization']
    search_fields = ['name', 'description']
    ordering = ['organization', 'priority', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ScoreHistory)
class ScoreHistoryAdmin(admin.ModelAdmin):
    list_display = ['contact', 'reason', 'points_delta', 'score_before', 'score_after', 'created_at']
    list_filter = ['reason']
    search_fields = ['contact__email', 'note']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ScoreThreshold)
class ScoreThresholdAdmin(admin.ModelAdmin):
    list_display = ['label', 'organization', 'min_score', 'engagement_level', 'color']
    list_filter = ['organization', 'engagement_level']
    search_fields = ['label']
    ordering = ['organization', 'min_score']
    readonly_fields = ['id', 'created_at', 'updated_at']
