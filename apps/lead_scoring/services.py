"""
Lead Scoring service layer.

Design principles:
  - Demographic rules are recalculated from scratch on every full recalc.
  - Behavioral rules apply an immediate delta when the event fires.
  - The service always saves with a fixed update_fields set so signal handlers
    can detect the write and skip re-triggering (anti-loop guard).
  - All public methods absorb exceptions at the call site; callers are expected
    to handle errors via Celery retry.
"""
import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone

from .models import ScoringRule, ScoreHistory, ScoreThreshold
from apps.contacts.models import Contact

logger = logging.getLogger(__name__)

# Score is clamped to [0, SCORE_MAX]
SCORE_MAX = 1000

# The exact update_fields the service writes — used by signals as an anti-loop guard
SCORE_UPDATE_FIELDS = frozenset({'lead_score', 'engagement_level', 'updated_at'})


class LeadScoringService:
    """Core service for all lead score computation and mutation."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def recalculate_contact(contact: Contact, reason: str = 'recalculation') -> tuple:
        """
        Re-evaluate all active demographic rules for a contact and update score.

        Returns (new_score, engagement_level).
        Writes ONE ScoreHistory entry if the score or level changed.
        Fires workflow threshold trigger after update.
        """
        org = contact.organization
        rules = ScoringRule.objects.filter(
            organization=org,
            rule_type=ScoringRule.RULE_TYPE_DEMOGRAPHIC,
            is_active=True,
            deleted_at__isnull=True,
        ).order_by('priority')

        raw_score = 0
        for rule in rules:
            try:
                if LeadScoringService._evaluate_condition(rule.condition, contact):
                    raw_score += rule.points
            except Exception as e:
                logger.warning(f"Error evaluating rule {rule.id}: {e}")

        new_score = LeadScoringService._clamp(raw_score)
        engagement = LeadScoringService.resolve_engagement_level(new_score, org)

        old_score = contact.lead_score
        old_level = contact.engagement_level

        if new_score != old_score or engagement != old_level:
            with transaction.atomic():
                Contact.objects.filter(pk=contact.pk).update(
                    lead_score=new_score,
                    engagement_level=engagement,
                    updated_at=timezone.now(),
                )
                contact.lead_score = new_score
                contact.engagement_level = engagement
                ScoreHistory.objects.create(
                    contact=contact,
                    rule=None,
                    reason=ScoreHistory.REASON_RECALC,
                    points_delta=new_score - old_score,
                    score_before=old_score,
                    score_after=new_score,
                    note=reason,
                )

            LeadScoringService._fire_threshold_trigger(contact, old_score, new_score)

        return new_score, engagement

    @staticmethod
    def apply_behavioral_rule(
        contact: Contact, rule: ScoringRule, note: str = ''
    ) -> int:
        """
        Apply a behavioral rule's point delta to a contact immediately.

        Returns the new score.
        Fires workflow threshold trigger after update.
        """
        old_score = contact.lead_score
        new_score = LeadScoringService._clamp(old_score + rule.points)
        engagement = LeadScoringService.resolve_engagement_level(
            new_score, contact.organization
        )

        with transaction.atomic():
            Contact.objects.filter(pk=contact.pk).update(
                lead_score=new_score,
                engagement_level=engagement,
                updated_at=timezone.now(),
            )
            contact.lead_score = new_score
            contact.engagement_level = engagement
            ScoreHistory.objects.create(
                contact=contact,
                rule=rule,
                reason=ScoreHistory.REASON_RULE,
                points_delta=rule.points,
                score_before=old_score,
                score_after=new_score,
                note=note or rule.name,
            )

        LeadScoringService._fire_threshold_trigger(contact, old_score, new_score)
        return new_score

    @staticmethod
    def manual_adjust(
        contact: Contact,
        points_delta: int,
        note: str,
        adjusted_by_user=None,
    ) -> int:
        """
        Manually adjust a contact's score by a signed delta.

        Returns the new score.
        """
        old_score = contact.lead_score
        new_score = LeadScoringService._clamp(old_score + points_delta)
        engagement = LeadScoringService.resolve_engagement_level(
            new_score, contact.organization
        )

        with transaction.atomic():
            Contact.objects.filter(pk=contact.pk).update(
                lead_score=new_score,
                engagement_level=engagement,
                updated_at=timezone.now(),
            )
            contact.lead_score = new_score
            contact.engagement_level = engagement
            ScoreHistory.objects.create(
                contact=contact,
                rule=None,
                reason=ScoreHistory.REASON_MANUAL,
                points_delta=points_delta,
                score_before=old_score,
                score_after=new_score,
                note=note,
            )

        LeadScoringService._fire_threshold_trigger(contact, old_score, new_score)
        return new_score

    @staticmethod
    def preview_score(contact: Contact) -> dict:
        """
        Simulate a full recalculation without saving.
        Returns {current_score, projected_score, matched_rules, engagement_level}.
        """
        org = contact.organization
        rules = ScoringRule.objects.filter(
            organization=org,
            rule_type=ScoringRule.RULE_TYPE_DEMOGRAPHIC,
            is_active=True,
            deleted_at__isnull=True,
        ).order_by('priority')

        matched = []
        raw_score = 0
        for rule in rules:
            try:
                if LeadScoringService._evaluate_condition(rule.condition, contact):
                    matched.append({
                        'id': str(rule.id),
                        'name': rule.name,
                        'points': rule.points,
                    })
                    raw_score += rule.points
            except Exception as e:
                logger.warning(f"Error previewing rule {rule.id}: {e}")

        projected = LeadScoringService._clamp(raw_score)
        return {
            'current_score': contact.lead_score,
            'projected_score': projected,
            'matched_rules': matched,
            'engagement_level': LeadScoringService.resolve_engagement_level(
                projected, org
            ),
        }

    @staticmethod
    def resolve_engagement_level(score: int, organization) -> str:
        """
        Return the engagement_level label for a given score using org thresholds.
        Falls back to 'none' when no thresholds are configured.
        """
        thresholds = ScoreThreshold.objects.filter(
            organization=organization
        ).order_by('-min_score')

        for threshold in thresholds:
            if score >= threshold.min_score:
                return threshold.engagement_level

        return 'none'

    @staticmethod
    def bulk_recalculate(organization) -> int:
        """
        Re-evaluate demographic rules for every contact in an organization.
        Processes contacts in chunks to avoid memory pressure.
        Returns the count of contacts whose score changed.
        """
        updated = 0
        contacts = Contact.objects.filter(organization=organization).iterator(
            chunk_size=100
        )
        for contact in contacts:
            try:
                old = contact.lead_score
                new, _ = LeadScoringService.recalculate_contact(contact)
                if new != old:
                    updated += 1
            except Exception as e:
                logger.exception(
                    f"Error recalculating score for contact {contact.id}: {e}"
                )
        return updated

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(score: int) -> int:
        return max(0, min(score, SCORE_MAX))

    @staticmethod
    def _fire_threshold_trigger(contact: Contact, old_score: int, new_score: int):
        """Fire workflow threshold triggers after a score update."""
        try:
            from apps.workflows.services import WorkflowTriggerService
            WorkflowTriggerService.trigger_lead_score_threshold(
                contact, old_score, new_score
            )
        except Exception as e:
            logger.warning(f"Error firing score threshold trigger: {e}")

    @staticmethod
    def _evaluate_condition(condition: dict, contact: Contact) -> bool:
        """
        Pure-Python evaluation of a demographic rule condition against an
        in-memory Contact instance.  No Q objects — returns a bool.

        Condition schema:
            {"field": "company", "operator": "is_not_empty", "value": ""}
        Custom fields:
            {"field": "custom.industry", "operator": "equals", "value": "Tech"}
        """
        if not condition:
            return False

        field = condition.get('field', '')
        operator = condition.get('operator', '')
        value = condition.get('value')

        if not field or not operator:
            return False

        # Resolve the actual value from the contact
        if field.startswith('custom.'):
            key = field[7:]
            actual = contact.custom_fields.get(key)
        elif field == 'is_subscribed':
            actual = contact.is_subscribed
        elif field == 'is_verified':
            actual = contact.is_verified
        elif hasattr(contact, field):
            actual = getattr(contact, field)
        else:
            actual = None

        return LeadScoringService._apply_operator(operator, actual, value)

    @staticmethod
    def _apply_operator(operator: str, actual, value) -> bool:
        """Apply a comparison operator between actual contact value and rule value."""

        # Boolean operators
        if operator == 'is_true':
            return bool(actual)
        if operator == 'is_false':
            return not bool(actual)

        # Null / empty checks (work on all types)
        if operator == 'is_empty':
            return actual is None or actual == '' or actual == []
        if operator == 'is_not_empty':
            return actual is not None and actual != '' and actual != []

        # Date / numeric comparisons
        if operator in ('greater_than', 'less_than', 'greater_or_equal', 'less_or_equal'):
            try:
                a = float(actual)
                v = float(value)
                if operator == 'greater_than':
                    return a > v
                if operator == 'less_than':
                    return a < v
                if operator == 'greater_or_equal':
                    return a >= v
                if operator == 'less_or_equal':
                    return a <= v
            except (TypeError, ValueError):
                return False

        # String comparisons (case-insensitive)
        actual_str = str(actual or '').lower().strip()
        value_str = str(value or '').lower().strip()

        if operator == 'equals':
            return actual_str == value_str
        if operator == 'not_equals':
            return actual_str != value_str
        if operator == 'contains':
            return value_str in actual_str
        if operator == 'not_contains':
            return value_str not in actual_str
        if operator == 'starts_with':
            return actual_str.startswith(value_str)
        if operator == 'ends_with':
            return actual_str.endswith(value_str)
        if operator == 'in':
            values = value if isinstance(value, list) else [value]
            return actual_str in [str(v).lower().strip() for v in values]
        if operator == 'not_in':
            values = value if isinstance(value, list) else [value]
            return actual_str not in [str(v).lower().strip() for v in values]

        logger.warning(f"Unknown operator in lead scoring condition: {operator}")
        return False
