"""
Services for the CRM & Pipeline app.
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone

from .models import Pipeline, Stage, Deal, DealContact, Activity, DealStageHistory, CRMTask, Company

logger = logging.getLogger(__name__)


class PipelineService:
    """Service for pipeline operations."""

    DEFAULT_STAGES = [
        {'name': 'Qualification', 'position': 0, 'stage_type': 'open', 'default_probability': 10, 'color': '#6366f1'},
        {'name': 'Proposal', 'position': 1, 'stage_type': 'open', 'default_probability': 30, 'color': '#8b5cf6'},
        {'name': 'Negotiation', 'position': 2, 'stage_type': 'open', 'default_probability': 60, 'color': '#a855f7'},
        {'name': 'Closed Won', 'position': 3, 'stage_type': 'won', 'default_probability': 100, 'color': '#22c55e'},
        {'name': 'Closed Lost', 'position': 4, 'stage_type': 'lost', 'default_probability': 0, 'color': '#ef4444'},
    ]

    @staticmethod
    @transaction.atomic
    def create_default_pipeline(organization, created_by=None):
        """Create a default pipeline with standard stages."""
        pipeline = Pipeline.objects.create(
            organization=organization,
            name='Sales Pipeline',
            description='Default sales pipeline',
            is_default=True,
            created_by=created_by,
        )

        for stage_data in PipelineService.DEFAULT_STAGES:
            Stage.objects.create(pipeline=pipeline, **stage_data)

        return pipeline

    @staticmethod
    def get_or_create_default(organization, user=None):
        """Return the default pipeline, creating one if none exists."""
        pipeline = Pipeline.objects.filter(
            organization=organization, is_default=True
        ).first()

        if not pipeline:
            pipeline = PipelineService.create_default_pipeline(organization, created_by=user)

        return pipeline

    @staticmethod
    @transaction.atomic
    def reorder_stages(pipeline, stage_ids):
        """Bulk-update stage positions based on ordered list of IDs."""
        stages = Stage.objects.filter(pipeline=pipeline, id__in=stage_ids)
        stage_map = {str(s.id): s for s in stages}

        for position, stage_id in enumerate(stage_ids):
            stage = stage_map.get(str(stage_id))
            if stage:
                stage.position = position
                stage.save(update_fields=['position'])


class DealService:
    """Service for deal operations."""

    @staticmethod
    @transaction.atomic
    def create_deal(organization, data, created_by=None):
        """Create a deal, link contacts, and record initial stage history."""
        contact_ids = data.pop('contact_ids', [])

        deal = Deal.objects.create(
            organization=organization,
            created_by=created_by,
            **data
        )

        # Record initial stage history
        DealStageHistory.objects.create(
            deal=deal,
            from_stage=None,
            to_stage=deal.stage,
            moved_by=created_by,
        )

        # Link contacts
        if deal.primary_contact:
            DealContact.objects.get_or_create(
                deal=deal,
                contact=deal.primary_contact,
                defaults={'role': 'primary', 'is_primary': True}
            )

        for contact_id in contact_ids:
            DealContact.objects.get_or_create(
                deal=deal,
                contact_id=contact_id,
                defaults={'role': 'other', 'is_primary': False}
            )

        # Update pipeline stats
        DealService.update_pipeline_stats(deal.pipeline)

        # Fire workflow trigger
        try:
            from apps.workflows.services import WorkflowTriggerService
            WorkflowTriggerService.trigger_deal_created(deal)
        except Exception:
            logger.exception("Error triggering deal_created workflow")

        return deal

    @staticmethod
    @transaction.atomic
    def move_deal(deal, to_stage_id, moved_by=None, position=None):
        """Move deal to a new stage, record history, auto-update status."""
        from_stage = deal.stage
        to_stage = Stage.objects.get(id=to_stage_id)

        deal.stage = to_stage
        deal.probability = to_stage.default_probability

        if position is not None:
            deal.position = position

        # Auto-update status based on stage type
        if to_stage.stage_type == 'won' and deal.status != 'won':
            deal.status = 'won'
            deal.closed_at = timezone.now()
        elif to_stage.stage_type == 'lost' and deal.status != 'lost':
            deal.status = 'lost'
            deal.closed_at = timezone.now()
        elif to_stage.stage_type == 'open' and deal.status != 'open':
            deal.status = 'open'
            deal.closed_at = None

        deal.save()

        # Record history
        DealStageHistory.objects.create(
            deal=deal,
            from_stage=from_stage,
            to_stage=to_stage,
            moved_by=moved_by,
        )

        # Update pipeline stats
        DealService.update_pipeline_stats(deal.pipeline)

        # Fire workflow trigger
        try:
            from apps.workflows.services import WorkflowTriggerService
            WorkflowTriggerService.trigger_deal_stage_changed(deal, from_stage, to_stage)
        except Exception:
            logger.exception("Error triggering deal_stage_changed workflow")

        return deal

    @staticmethod
    @transaction.atomic
    def win_deal(deal, win_reason='', closed_by=None):
        """Mark deal as won."""
        won_stage = Stage.objects.filter(
            pipeline=deal.pipeline, stage_type='won'
        ).first()

        from_stage = deal.stage
        deal.status = 'won'
        deal.win_reason = win_reason
        deal.closed_at = timezone.now()
        deal.probability = 100

        if won_stage:
            deal.stage = won_stage

        deal.save()

        DealStageHistory.objects.create(
            deal=deal,
            from_stage=from_stage,
            to_stage=deal.stage,
            moved_by=closed_by,
        )

        DealService.update_pipeline_stats(deal.pipeline)
        return deal

    @staticmethod
    @transaction.atomic
    def lose_deal(deal, loss_reason='', closed_by=None):
        """Mark deal as lost."""
        lost_stage = Stage.objects.filter(
            pipeline=deal.pipeline, stage_type='lost'
        ).first()

        from_stage = deal.stage
        deal.status = 'lost'
        deal.loss_reason = loss_reason
        deal.closed_at = timezone.now()
        deal.probability = 0

        if lost_stage:
            deal.stage = lost_stage

        deal.save()

        DealStageHistory.objects.create(
            deal=deal,
            from_stage=from_stage,
            to_stage=deal.stage,
            moved_by=closed_by,
        )

        DealService.update_pipeline_stats(deal.pipeline)
        return deal

    @staticmethod
    @transaction.atomic
    def reopen_deal(deal, to_stage_id=None):
        """Reopen a closed deal."""
        from_stage = deal.stage

        if to_stage_id:
            to_stage = Stage.objects.get(id=to_stage_id)
        else:
            # Default to first open stage
            to_stage = Stage.objects.filter(
                pipeline=deal.pipeline, stage_type='open'
            ).order_by('position').first()

        deal.status = 'open'
        deal.closed_at = None
        deal.win_reason = ''
        deal.loss_reason = ''

        if to_stage:
            deal.stage = to_stage
            deal.probability = to_stage.default_probability

        deal.save()

        DealStageHistory.objects.create(
            deal=deal,
            from_stage=from_stage,
            to_stage=deal.stage,
        )

        DealService.update_pipeline_stats(deal.pipeline)
        return deal

    @staticmethod
    def update_pipeline_stats(pipeline):
        """Recalculate cached pipeline stats from open deals."""
        stats = Deal.objects.filter(
            pipeline=pipeline, status='open'
        ).aggregate(
            total_deals=Count('id'),
            total_value=Sum('value')
        )

        pipeline.total_deals = stats['total_deals'] or 0
        pipeline.total_value = stats['total_value'] or Decimal('0')
        pipeline.save(update_fields=['total_deals', 'total_value'])

    @staticmethod
    @transaction.atomic
    def reorder_deals_in_stage(stage, deal_ids):
        """Bulk-update deal positions within a stage."""
        deals = Deal.objects.filter(stage=stage, id__in=deal_ids)
        deal_map = {str(d.id): d for d in deals}

        for position, deal_id in enumerate(deal_ids):
            deal = deal_map.get(str(deal_id))
            if deal:
                deal.position = position
                deal.save(update_fields=['position'])

    @staticmethod
    def get_kanban_data(pipeline):
        """Return stages with their deals ordered for kanban display."""
        stages = pipeline.stages.all().order_by('position')
        kanban = []

        for stage in stages:
            deals = Deal.objects.filter(
                stage=stage, pipeline=pipeline
            ).select_related(
                'primary_contact', 'assigned_to'
            ).order_by('position', '-created_at')

            total_value = deals.filter(status='open').aggregate(
                total=Sum('value')
            )['total'] or Decimal('0')

            kanban.append({
                'stage': stage,
                'deals': deals,
                'deal_count': deals.count(),
                'total_value': total_value,
            })

        return kanban


class ActivityService:
    """Service for activity operations."""

    @staticmethod
    def log_activity(organization, data, created_by=None):
        """Create a new activity and update deal's last_activity_at."""
        activity = Activity.objects.create(
            organization=organization,
            created_by=created_by,
            **data
        )
        if activity.deal_id:
            Deal.objects.filter(id=activity.deal_id).update(
                last_activity_at=timezone.now(),
                is_rotting=False,
            )
        return activity

    @staticmethod
    def complete_activity(activity):
        """Mark activity as completed and update deal's last_activity_at."""
        activity.is_completed = True
        activity.completed_at = timezone.now()
        activity.save(update_fields=['is_completed', 'completed_at'])
        if activity.deal_id:
            Deal.objects.filter(id=activity.deal_id).update(
                last_activity_at=timezone.now(),
                is_rotting=False,
            )
        return activity

    @staticmethod
    def get_timeline(deal_id=None, contact_id=None, limit=50):
        """Get activity timeline for a deal or contact."""
        qs = Activity.objects.select_related(
            'deal', 'contact', 'created_by', 'assigned_to'
        )

        if deal_id:
            qs = qs.filter(deal_id=deal_id)
        elif contact_id:
            qs = qs.filter(contact_id=contact_id)

        return qs.order_by('-created_at')[:limit]


class CRMAnalyticsService:
    """Service for CRM analytics and reporting."""

    @staticmethod
    def get_pipeline_value_by_stage(pipeline):
        """Sum of open deal values grouped by stage."""
        stages = pipeline.stages.all().order_by('position')
        result = []

        for stage in stages:
            agg = Deal.objects.filter(
                pipeline=pipeline, stage=stage, status='open'
            ).aggregate(
                total_value=Sum('value'),
                deal_count=Count('id')
            )
            result.append({
                'stage_id': str(stage.id),
                'stage_name': stage.name,
                'stage_color': stage.color,
                'total_value': float(agg['total_value'] or 0),
                'deal_count': agg['deal_count'] or 0,
            })

        return result

    @staticmethod
    def get_win_rate(organization, days=30):
        """Calculate win rate over the given period."""
        since = timezone.now() - timezone.timedelta(days=days)
        closed_deals = Deal.objects.filter(
            organization=organization,
            status__in=['won', 'lost'],
            closed_at__gte=since,
        )
        total = closed_deals.count()
        won = closed_deals.filter(status='won').count()
        return (won / total * 100) if total > 0 else 0

    @staticmethod
    def get_average_deal_size(organization, days=30):
        """Average value of won deals."""
        since = timezone.now() - timezone.timedelta(days=days)
        result = Deal.objects.filter(
            organization=organization,
            status='won',
            closed_at__gte=since,
        ).aggregate(avg=Avg('value'))
        return float(result['avg'] or 0)

    @staticmethod
    def get_conversion_rates(pipeline, days=30):
        """Per-stage conversion rate."""
        since = timezone.now() - timezone.timedelta(days=days)
        stages = pipeline.stages.filter(stage_type='open').order_by('position')
        result = []

        for stage in stages:
            entered = DealStageHistory.objects.filter(
                deal__pipeline=pipeline,
                to_stage=stage,
                created_at__gte=since,
            ).values('deal').distinct().count()

            progressed = DealStageHistory.objects.filter(
                deal__pipeline=pipeline,
                from_stage=stage,
                created_at__gte=since,
            ).values('deal').distinct().count()

            rate = (progressed / entered * 100) if entered > 0 else 0
            result.append({
                'stage_id': str(stage.id),
                'stage_name': stage.name,
                'entered': entered,
                'progressed': progressed,
                'conversion_rate': round(rate, 1),
            })

        return result

    @staticmethod
    def get_pipeline_summary(organization, days=30):
        """Combined pipeline summary stats."""
        since = timezone.now() - timezone.timedelta(days=days)
        open_deals = Deal.objects.filter(
            organization=organization, status='open'
        )
        won_deals = Deal.objects.filter(
            organization=organization, status='won', closed_at__gte=since
        )

        return {
            'open_deals_count': open_deals.count(),
            'open_deals_value': float(open_deals.aggregate(total=Sum('value'))['total'] or 0),
            'won_deals_count': won_deals.count(),
            'won_deals_value': float(won_deals.aggregate(total=Sum('value'))['total'] or 0),
            'win_rate': CRMAnalyticsService.get_win_rate(organization, days),
            'avg_deal_size': CRMAnalyticsService.get_average_deal_size(organization, days),
        }


class CRMTaskService:
    """Service for CRM task operations."""

    @staticmethod
    def create_task(organization, data, created_by=None):
        return CRMTask.objects.create(
            organization=organization,
            created_by=created_by,
            **data
        )

    @staticmethod
    def complete_task(task):
        task.status = 'done'
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at'])
        return task

    @staticmethod
    def get_overdue_count(organization):
        from django.utils.timezone import now
        today = now().date()
        return CRMTask.objects.filter(
            organization=organization,
            status__in=['todo', 'in_progress'],
            due_date__lt=today,
        ).count()


class ForecastingService:
    """Service for revenue forecasting."""

    @staticmethod
    def get_forecast(organization, months=6):
        """Return weighted and best-case revenue grouped by close month."""
        from datetime import date
        from calendar import month_abbr

        today = date.today()
        open_deals = Deal.objects.filter(
            organization=organization,
            status='open',
        ).values('close_date', 'value', 'probability', 'weighted_value')

        # Bucket by close month
        buckets: dict = {}
        no_date_bucket = {'month': None, 'label': 'No Date', 'weighted': 0.0, 'best_case': 0.0, 'deal_count': 0}

        for deal in open_deals:
            cd = deal['close_date']
            if cd is None:
                no_date_bucket['weighted'] += float(deal['weighted_value'])
                no_date_bucket['best_case'] += float(deal['value'])
                no_date_bucket['deal_count'] += 1
            else:
                key = (cd.year, cd.month)
                if key not in buckets:
                    buckets[key] = {
                        'month': cd.strftime('%Y-%m'),
                        'label': f"{month_abbr[cd.month]} {cd.year}",
                        'weighted': 0.0,
                        'best_case': 0.0,
                        'deal_count': 0,
                    }
                buckets[key]['weighted'] += float(deal['weighted_value'])
                buckets[key]['best_case'] += float(deal['value'])
                buckets[key]['deal_count'] += 1

        # Sort buckets chronologically
        sorted_buckets = [buckets[k] for k in sorted(buckets.keys())]
        if no_date_bucket['deal_count'] > 0:
            sorted_buckets.append(no_date_bucket)

        # Summary totals
        total_weighted = sum(b['weighted'] for b in sorted_buckets)
        total_best_case = sum(b['best_case'] for b in sorted_buckets)
        rotting_count = Deal.objects.filter(organization=organization, status='open', is_rotting=True).count()

        return {
            'buckets': sorted_buckets,
            'total_weighted': total_weighted,
            'total_best_case': total_best_case,
            'open_deals_count': sum(b['deal_count'] for b in sorted_buckets),
            'rotting_deals_count': rotting_count,
        }


class CompanyService:
    """Service for company / account operations."""

    @staticmethod
    def create_company(organization, data, created_by=None):
        if created_by and 'owner' not in data:
            data = {**data, 'owner': created_by}
        return Company.objects.create(organization=organization, **data)

    @staticmethod
    def get_contacts(company):
        from apps.contacts.models import Contact
        return Contact.objects.filter(company_ref=company).select_related('organization')

    @staticmethod
    def get_deals(company):
        return Deal.objects.filter(company=company).select_related('stage', 'pipeline', 'primary_contact')

    @staticmethod
    def get_activities(company):
        deal_ids = Deal.objects.filter(company=company).values_list('id', flat=True)
        contact_ids = company.contacts.values_list('id', flat=True)
        return Activity.objects.filter(
            Q(deal_id__in=deal_ids) | Q(contact_id__in=contact_ids)
        ).select_related('deal', 'contact', 'created_by').order_by('-created_at')[:50]
