"""
Serializers for the CRM & Pipeline app.
"""
from rest_framework import serializers
from django.db import transaction
from .models import Pipeline, Stage, Deal, DealContact, Activity, DealStageHistory, CRMTask, Company
from apps.contacts.models import Contact


class StageSerializer(serializers.ModelSerializer):
    """Serializer for pipeline stages."""

    class Meta:
        model = Stage
        fields = [
            'id', 'name', 'color', 'position', 'stage_type',
            'default_probability', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class StageCreateSerializer(serializers.Serializer):
    """Serializer for creating a stage within a pipeline."""
    name = serializers.CharField(max_length=255)
    color = serializers.CharField(max_length=7, default='#6366f1')
    stage_type = serializers.ChoiceField(
        choices=Stage.STAGE_TYPE_CHOICES, default='open'
    )
    default_probability = serializers.IntegerField(min_value=0, max_value=100, default=50)

    def validate_name(self, value):
        """
        Stage names are unique per pipeline.

        Enforced here as well as by the model so a repeated name is a field
        error the dialog can show, rather than the IntegrityError the database
        raises, which surfaced as "An unexpected error occurred".
        """
        pipeline = self.context.get('pipeline')
        if pipeline and pipeline.stages.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError(
                f'This pipeline already has a stage named "{value.strip()}".'
            )
        return value


class StageReorderSerializer(serializers.Serializer):
    """Serializer for reordering stages."""
    stage_ids = serializers.ListField(child=serializers.UUIDField())


class PipelineListSerializer(serializers.ModelSerializer):
    """Serializer for pipeline list view."""
    stage_count = serializers.SerializerMethodField()

    class Meta:
        model = Pipeline
        fields = [
            'id', 'name', 'description', 'is_default',
            'total_deals', 'total_value', 'stage_count', 'created_at',
        ]

    def get_stage_count(self, obj):
        return obj.stages.count()


class PipelineSerializer(serializers.ModelSerializer):
    """Full pipeline detail serializer with nested stages."""
    stages = StageSerializer(many=True, read_only=True)
    stage_count = serializers.SerializerMethodField()

    class Meta:
        model = Pipeline
        fields = [
            'id', 'name', 'description', 'is_default',
            'total_deals', 'total_value', 'stages', 'stage_count',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total_deals', 'total_value', 'created_by', 'created_at', 'updated_at']

    def get_stage_count(self, obj):
        return obj.stages.count()


class PipelineCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a pipeline."""
    stages = StageCreateSerializer(many=True, required=False)

    class Meta:
        model = Pipeline
        fields = ['name', 'description', 'stages']

    def validate_stages(self, value):
        names = [s['name'].strip().lower() for s in value]
        duplicate = next((n for n in names if names.count(n) > 1), None)
        if duplicate:
            # The model enforces this with a unique constraint, which arrives
            # as a 500 rather than something the form can show.
            raise serializers.ValidationError(
                f'Two stages are both named "{duplicate}". Stage names must be unique.'
            )
        return value

    def to_representation(self, instance):
        # The create response listed only the fields that were sent, so it
        # carried no id and no stage ids -- the client could not address the
        # pipeline it had just made, which is what broke adding a stage next.
        return PipelineSerializer(instance, context=self.context).data

    @transaction.atomic
    def create(self, validated_data):
        stages_data = validated_data.pop('stages', [])
        pipeline = Pipeline.objects.create(**validated_data)

        if stages_data:
            for i, stage_data in enumerate(stages_data):
                stage_data['position'] = i
                Stage.objects.create(pipeline=pipeline, **stage_data)
        else:
            # Create default stages
            from .services import PipelineService
            for stage_data in PipelineService.DEFAULT_STAGES:
                Stage.objects.create(pipeline=pipeline, **stage_data)

        return pipeline


# Deal serializers

class DealContactSerializer(serializers.ModelSerializer):
    """Serializer for deal-contact relationships."""
    contact_name = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()

    class Meta:
        model = DealContact
        fields = ['id', 'contact', 'contact_name', 'contact_email', 'role', 'is_primary', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_contact_name(self, obj):
        return obj.contact.full_name

    def get_contact_email(self, obj):
        return obj.contact.email


class DealContactCreateSerializer(serializers.Serializer):
    """Serializer for adding a contact to a deal."""
    contact_id = serializers.UUIDField()
    role = serializers.ChoiceField(
        choices=DealContact.ROLE_CHOICES, default='other'
    )
    is_primary = serializers.BooleanField(default=False)


class DealStageHistorySerializer(serializers.ModelSerializer):
    """Serializer for deal stage history entries."""
    from_stage_name = serializers.SerializerMethodField()
    to_stage_name = serializers.SerializerMethodField()
    moved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DealStageHistory
        fields = ['id', 'from_stage_name', 'to_stage_name', 'moved_by_name', 'created_at']

    def get_from_stage_name(self, obj):
        return obj.from_stage.name if obj.from_stage else None

    def get_to_stage_name(self, obj):
        return obj.to_stage.name if obj.to_stage else None

    def get_moved_by_name(self, obj):
        if not obj.moved_by:
            return None
        name = f"{obj.moved_by.first_name} {obj.moved_by.last_name}".strip()
        return name or obj.moved_by.email


class DealListSerializer(serializers.ModelSerializer):
    """Compact serializer for deal list view."""
    stage_name = serializers.SerializerMethodField()
    stage_color = serializers.SerializerMethodField()
    primary_contact_name = serializers.SerializerMethodField()
    primary_contact_email = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            'id', 'title', 'status', 'value', 'currency', 'probability',
            'weighted_value', 'stage', 'stage_name', 'stage_color',
            'primary_contact', 'primary_contact_name', 'primary_contact_email',
            'priority', 'close_date', 'assigned_to', 'assigned_to_name',
            'company', 'company_name',
            'is_rotting', 'last_activity_at',
            'created_at',
        ]

    def get_company_name(self, obj):
        return obj.company.name if obj.company else None

    def get_stage_name(self, obj):
        return obj.stage.name if obj.stage else None

    def get_stage_color(self, obj):
        return obj.stage.color if obj.stage else None

    def get_primary_contact_name(self, obj):
        return obj.primary_contact.full_name if obj.primary_contact else None

    def get_primary_contact_email(self, obj):
        return obj.primary_contact.email if obj.primary_contact else None

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return None
        name = f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return name or obj.assigned_to.email


class DealSerializer(serializers.ModelSerializer):
    """Full deal detail serializer."""
    stage_name = serializers.SerializerMethodField()
    stage_color = serializers.SerializerMethodField()
    pipeline_name = serializers.SerializerMethodField()
    primary_contact_name = serializers.SerializerMethodField()
    primary_contact_email = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    contacts = serializers.SerializerMethodField()
    stage_history = serializers.SerializerMethodField()
    recent_activities = serializers.SerializerMethodField()
    activity_count = serializers.SerializerMethodField()
    stages = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            'id', 'title', 'description', 'status', 'priority',
            'value', 'currency', 'probability', 'weighted_value',
            'close_date', 'closed_at', 'win_reason', 'loss_reason',
            'position', 'pipeline', 'pipeline_name', 'stage', 'stage_name', 'stage_color',
            'primary_contact', 'primary_contact_name', 'primary_contact_email',
            'assigned_to', 'assigned_to_name',
            'created_by', 'created_by_name',
            'company', 'company_name',
            'contacts', 'stage_history', 'recent_activities', 'activity_count',
            'stages',
            'is_rotting', 'last_activity_at', 'rotting_threshold_days',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'weighted_value', 'closed_at',
            'created_by', 'created_at', 'updated_at',
        ]

    def get_stage_name(self, obj):
        return obj.stage.name if obj.stage else None

    def get_stage_color(self, obj):
        return obj.stage.color if obj.stage else None

    def get_pipeline_name(self, obj):
        return obj.pipeline.name if obj.pipeline else None

    def get_primary_contact_name(self, obj):
        return obj.primary_contact.full_name if obj.primary_contact else None

    def get_primary_contact_email(self, obj):
        return obj.primary_contact.email if obj.primary_contact else None

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return None
        name = f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return name or obj.assigned_to.email

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return name or obj.created_by.email

    def get_company_name(self, obj):
        return obj.company.name if obj.company else None

    def get_contacts(self, obj):
        dc = obj.deal_contacts.select_related('contact').all()
        return DealContactSerializer(dc, many=True).data

    def get_stage_history(self, obj):
        history = obj.stage_history.select_related(
            'from_stage', 'to_stage', 'moved_by'
        ).order_by('-created_at')[:20]
        return DealStageHistorySerializer(history, many=True).data

    def get_recent_activities(self, obj):
        activities = obj.activities.select_related(
            'created_by', 'assigned_to'
        ).order_by('-created_at')[:10]
        return ActivityListSerializer(activities, many=True).data

    def get_activity_count(self, obj):
        return obj.activities.count()

    def get_stages(self, obj):
        """Return all stages in the deal's pipeline for progress display."""
        stages = obj.pipeline.stages.all().order_by('position')
        return StageSerializer(stages, many=True).data


class DealCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a deal."""
    contact_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )

    class Meta:
        model = Deal
        fields = [
            'title', 'description', 'pipeline', 'stage', 'value', 'currency',
            'probability', 'priority', 'close_date', 'primary_contact',
            'assigned_to', 'contact_ids',
        ]

    def validate_stage(self, value):
        """Ensure stage belongs to the selected pipeline."""
        pipeline = self.initial_data.get('pipeline')
        if pipeline and value and str(value.pipeline_id) != str(pipeline):
            raise serializers.ValidationError(
                "Stage does not belong to the selected pipeline."
            )
        return value

    def validate_primary_contact(self, value):
        """Ensure contact belongs to the user's organization."""
        if value:
            request = self.context.get('request')
            if value.organization != request.user.organization:
                raise serializers.ValidationError(
                    "Contact does not belong to your organization."
                )
        return value


class DealUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a deal."""

    class Meta:
        model = Deal
        fields = [
            'title', 'description', 'value', 'currency', 'probability',
            'priority', 'close_date', 'primary_contact', 'assigned_to',
        ]


class DealMoveSerializer(serializers.Serializer):
    """Serializer for moving a deal to a different stage."""
    stage_id = serializers.UUIDField()
    position = serializers.IntegerField(required=False, min_value=0)


class DealWinSerializer(serializers.Serializer):
    """Serializer for marking a deal as won."""
    win_reason = serializers.CharField(max_length=255, required=False, default='')


class DealLoseSerializer(serializers.Serializer):
    """Serializer for marking a deal as lost."""
    loss_reason = serializers.CharField(max_length=255, required=False, default='')


class DealKanbanSerializer(serializers.ModelSerializer):
    """Compact serializer for kanban card display."""
    primary_contact_name = serializers.SerializerMethodField()
    primary_contact_email = serializers.SerializerMethodField()
    activity_count = serializers.SerializerMethodField()
    days_since_activity = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            'id', 'title', 'value', 'currency', 'probability', 'status',
            'primary_contact_name', 'primary_contact_email',
            'priority', 'close_date', 'position', 'activity_count',
            'is_rotting', 'last_activity_at', 'days_since_activity',
        ]

    def get_primary_contact_name(self, obj):
        return obj.primary_contact.full_name if obj.primary_contact else None

    def get_primary_contact_email(self, obj):
        return obj.primary_contact.email if obj.primary_contact else None

    def get_activity_count(self, obj):
        return obj.activities.filter(is_completed=False).count()

    def get_days_since_activity(self, obj):
        from django.utils import timezone
        reference = obj.last_activity_at or obj.created_at
        return (timezone.now() - reference).days if reference else None


# Kanban stage serializer (stage + deals)
class KanbanStageSerializer(serializers.Serializer):
    """Serializer for a kanban column (stage + deals)."""
    stage = StageSerializer()
    deals = DealKanbanSerializer(many=True)
    deal_count = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)


# Activity serializers

class ActivityListSerializer(serializers.ModelSerializer):
    """Compact serializer for activity list."""
    deal_title = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id', 'activity_type', 'title', 'description',
            'due_date', 'is_completed', 'completed_at', 'duration',
            'deal', 'deal_title', 'contact', 'contact_name',
            'created_by_name', 'assigned_to', 'assigned_to_name',
            'created_at',
        ]

    def get_deal_title(self, obj):
        return obj.deal.title if obj.deal else None

    def get_contact_name(self, obj):
        return obj.contact.full_name if obj.contact else None

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return name or obj.created_by.email

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return None
        name = f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return name or obj.assigned_to.email


class ActivitySerializer(serializers.ModelSerializer):
    """Full activity detail serializer."""
    deal_title = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id', 'activity_type', 'title', 'description',
            'due_date', 'is_completed', 'completed_at', 'duration',
            'deal', 'deal_title', 'contact', 'contact_name',
            'created_by', 'created_by_name',
            'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_deal_title(self, obj):
        return obj.deal.title if obj.deal else None

    def get_contact_name(self, obj):
        return obj.contact.full_name if obj.contact else None

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return name or obj.created_by.email

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return None
        name = f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return name or obj.assigned_to.email


class ActivityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an activity."""

    class Meta:
        model = Activity
        fields = [
            'activity_type', 'title', 'description',
            'deal', 'contact', 'due_date', 'duration', 'assigned_to',
        ]

    def validate_deal(self, value):
        if value:
            request = self.context.get('request')
            if value.organization != request.user.organization:
                raise serializers.ValidationError(
                    "Deal does not belong to your organization."
                )
        return value

    def validate_contact(self, value):
        if value:
            request = self.context.get('request')
            if value.organization != request.user.organization:
                raise serializers.ValidationError(
                    "Contact does not belong to your organization."
                )
        return value


class PipelineAnalyticsSerializer(serializers.Serializer):
    """Response serializer for pipeline analytics."""
    value_by_stage = serializers.ListField()
    win_rate = serializers.FloatField()
    avg_deal_size = serializers.FloatField()
    conversion_rates = serializers.ListField()
    summary = serializers.DictField()


# CRM Task serializers

class CRMTaskListSerializer(serializers.ModelSerializer):
    """Compact task list serializer."""
    deal_title = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = CRMTask
        fields = [
            'id', 'title', 'priority', 'status', 'due_date', 'completed_at',
            'deal', 'deal_title', 'contact', 'contact_name',
            'assigned_to', 'assigned_to_name', 'is_overdue',
            'created_at',
        ]

    def get_deal_title(self, obj):
        return obj.deal.title if obj.deal else None

    def get_contact_name(self, obj):
        return obj.contact.full_name if obj.contact else None

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return None
        name = f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return name or obj.assigned_to.email

    def get_is_overdue(self, obj):
        from django.utils.timezone import now
        if obj.due_date and obj.status != 'done':
            return obj.due_date < now().date()
        return False


class CRMTaskSerializer(serializers.ModelSerializer):
    """Full task detail serializer."""
    deal_title = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = CRMTask
        fields = [
            'id', 'title', 'description', 'priority', 'status',
            'due_date', 'completed_at',
            'deal', 'deal_title', 'contact', 'contact_name',
            'assigned_to', 'assigned_to_name',
            'created_by', 'created_by_name',
            'is_overdue', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'completed_at', 'created_by', 'created_at', 'updated_at']

    def get_deal_title(self, obj):
        return obj.deal.title if obj.deal else None

    def get_contact_name(self, obj):
        return obj.contact.full_name if obj.contact else None

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return None
        name = f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return name or obj.assigned_to.email

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return name or obj.created_by.email

    def get_is_overdue(self, obj):
        from django.utils.timezone import now
        if obj.due_date and obj.status != 'done':
            return obj.due_date < now().date()
        return False


class CRMTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating a task."""

    class Meta:
        model = CRMTask
        fields = [
            'title', 'description', 'priority', 'status',
            'due_date', 'deal', 'contact', 'assigned_to',
        ]


# Forecast serializer

class ForecastBucketSerializer(serializers.Serializer):
    month = serializers.CharField(allow_null=True)
    label = serializers.CharField()
    weighted = serializers.FloatField()
    best_case = serializers.FloatField()
    deal_count = serializers.IntegerField()


class ForecastSerializer(serializers.Serializer):
    buckets = ForecastBucketSerializer(many=True)
    total_weighted = serializers.FloatField()
    total_best_case = serializers.FloatField()
    open_deals_count = serializers.IntegerField()
    rotting_deals_count = serializers.IntegerField()


# Company serializers

class CompanyListSerializer(serializers.ModelSerializer):
    """Compact serializer for company list."""
    contact_count = serializers.SerializerMethodField()
    deal_count = serializers.SerializerMethodField()
    open_deal_value = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'website', 'domain', 'industry', 'size',
            'phone', 'owner', 'owner_name',
            'contact_count', 'deal_count', 'open_deal_value',
            'created_at',
        ]

    def get_contact_count(self, obj):
        return obj.contacts.count()

    def get_deal_count(self, obj):
        return obj.deals.count()

    def get_open_deal_value(self, obj):
        from django.db.models import Sum
        result = obj.deals.filter(status='open').aggregate(total=Sum('value'))
        return float(result['total'] or 0)

    def get_owner_name(self, obj):
        if not obj.owner:
            return None
        name = f"{obj.owner.first_name} {obj.owner.last_name}".strip()
        return name or obj.owner.email


class CompanySerializer(serializers.ModelSerializer):
    """Full company detail serializer."""
    contact_count = serializers.SerializerMethodField()
    deal_count = serializers.SerializerMethodField()
    open_deal_value = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'website', 'domain', 'industry', 'size',
            'annual_revenue', 'phone', 'address', 'description',
            'owner', 'owner_name',
            'contact_count', 'deal_count', 'open_deal_value',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_contact_count(self, obj):
        return obj.contacts.count()

    def get_deal_count(self, obj):
        return obj.deals.count()

    def get_open_deal_value(self, obj):
        from django.db.models import Sum
        result = obj.deals.filter(status='open').aggregate(total=Sum('value'))
        return float(result['total'] or 0)

    def get_owner_name(self, obj):
        if not obj.owner:
            return None
        name = f"{obj.owner.first_name} {obj.owner.last_name}".strip()
        return name or obj.owner.email


class CompanyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating a company."""

    class Meta:
        model = Company
        fields = [
            'name', 'website', 'domain', 'industry', 'size',
            'annual_revenue', 'phone', 'address', 'description', 'owner',
        ]
