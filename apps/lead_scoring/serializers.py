"""
Serializers for the Lead Scoring app.
"""
from rest_framework import serializers
from .models import ScoringRule, ScoreHistory, ScoreThreshold

VALID_OPERATORS = {
    'equals', 'not_equals', 'contains', 'not_contains',
    'starts_with', 'ends_with', 'is_empty', 'is_not_empty',
    'greater_than', 'less_than', 'greater_or_equal', 'less_or_equal',
    'is_true', 'is_false', 'in', 'not_in',
}


class ScoringRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoringRule
        fields = [
            'id', 'name', 'description', 'rule_type', 'points',
            'is_active', 'priority', 'condition', 'event_type',
            'event_filter', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        rule_type = data.get('rule_type') or (
            self.instance.rule_type if self.instance else None
        )
        if rule_type == ScoringRule.RULE_TYPE_DEMOGRAPHIC:
            condition = data.get('condition') or {}
            if not condition.get('field'):
                raise serializers.ValidationError(
                    {'condition': 'Demographic rules require a condition field.'}
                )
            if not condition.get('operator'):
                raise serializers.ValidationError(
                    {'condition': 'Demographic rules require a condition operator.'}
                )
            if condition['operator'] not in VALID_OPERATORS:
                raise serializers.ValidationError(
                    {'condition': f"Unknown operator: {condition['operator']}"}
                )
        elif rule_type == ScoringRule.RULE_TYPE_BEHAVIORAL:
            event_type = data.get('event_type') or (
                self.instance.event_type if self.instance else ''
            )
            if not event_type:
                raise serializers.ValidationError(
                    {'event_type': 'Behavioral rules require an event_type.'}
                )
        return data


class ScoreThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreThreshold
        fields = [
            'id', 'label', 'min_score', 'color',
            'engagement_level', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScoreThresholdInputSerializer(serializers.Serializer):
    """Used for bulk-update — no id field."""
    label = serializers.CharField(max_length=50)
    min_score = serializers.IntegerField()
    color = serializers.CharField(max_length=20, default='blue')
    engagement_level = serializers.ChoiceField(
        choices=['high', 'medium', 'low', 'none']
    )


class BulkUpdateThresholdsSerializer(serializers.Serializer):
    thresholds = ScoreThresholdInputSerializer(many=True)

    def validate_thresholds(self, value):
        if not value:
            raise serializers.ValidationError(
                'At least one threshold is required.'
            )
        labels = [t['label'] for t in value]
        if len(labels) != len(set(labels)):
            raise serializers.ValidationError('Threshold labels must be unique.')
        return value


class RuleRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoringRule
        fields = ['id', 'name', 'rule_type']


class ScoreHistorySerializer(serializers.ModelSerializer):
    rule = RuleRefSerializer(read_only=True)

    class Meta:
        model = ScoreHistory
        fields = [
            'id', 'rule', 'reason', 'points_delta',
            'score_before', 'score_after', 'note', 'created_at',
        ]
        read_only_fields = fields


class ManualAdjustSerializer(serializers.Serializer):
    points_delta = serializers.IntegerField()
    note = serializers.CharField(max_length=255, default='', allow_blank=True)

    def validate_points_delta(self, value):
        if value == 0:
            raise serializers.ValidationError('points_delta must be non-zero.')
        return value


class ReorderRulesSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1
    )
