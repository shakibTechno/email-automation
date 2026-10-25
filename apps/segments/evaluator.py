"""
Segment Evaluator - Rule engine for evaluating segment conditions.
"""
import logging
from datetime import timedelta
from django.db.models import Q, Count, Exists, OuterRef
from django.utils import timezone

from apps.contacts.models import Contact, ContactTag
from apps.contacts import fields as contact_fields

logger = logging.getLogger(__name__)


class UnknownSegmentField(ValueError):
    """
    A rule names a field that does not exist.

    Its own type so the API can answer 400 with the field name instead of the
    500 an unresolvable Q() used to produce. Stored rules can contain one: a
    segment built on the old phantom "Status" field is still in the database
    even though the builder no longer offers it.
    """

    def __init__(self, field):
        self.field = field
        super().__init__(
            f'"{field}" is not a field that can be used in a segment rule.'
        )



# Field definitions with their types and available operators
# Derived from the contact field registry, not listed here.
#
# This was a hand-maintained copy, and it had already drifted: it advertised a
# "Status" field the Contact model has never had, so any rule built on it
# produced Q(status__iexact=...) and raised FieldError — a 500 on preview and
# on every later use of that segment. Generating the list means a field cannot
# be offered unless it exists.
#
# `tag` is not a column, so it is added explicitly; custom fields are merged in
# per organization by get_field_definitions().
FIELD_DEFINITIONS = {
    key: {'type': spec.type, 'label': spec.label, **({'options': list(spec.options)} if spec.options else {})}
    for key, spec in contact_fields.segmentable_specs().items()
}
FIELD_DEFINITIONS['tag'] = {'type': 'tag', 'label': 'Tag'}

# The registry describes a field's meaning (an email is not just a string);
# the operator table cares only about how it compares. One map rather than two
# vocabularies.
OPERATOR_TYPE_FOR = {
    'email': 'string',
    'phone': 'string',
    'url': 'string',
    'datetime': 'date',
}


# CustomField.FIELD_TYPE_CHOICES uses its own names for two of these.
CUSTOM_FIELD_TYPE_MAP = {
    'text': 'string',
    'dropdown': 'select',
}


def operator_type(field_type):
    return OPERATOR_TYPE_FOR.get(field_type, field_type)

# Operators by field type
OPERATORS_BY_TYPE = {
    'string': [
        ('equals', 'equals'),
        ('not_equals', 'does not equal'),
        ('contains', 'contains'),
        ('not_contains', 'does not contain'),
        ('starts_with', 'starts with'),
        ('ends_with', 'ends with'),
        ('is_empty', 'is empty'),
        ('is_not_empty', 'is not empty'),
    ],
    'number': [
        ('equals', 'equals'),
        ('not_equals', 'does not equal'),
        ('greater_than', 'greater than'),
        ('less_than', 'less than'),
        ('greater_or_equal', 'greater than or equal'),
        ('less_or_equal', 'less than or equal'),
        ('between', 'between'),
        ('is_empty', 'is empty'),
        ('is_not_empty', 'is not empty'),
    ],
    'date': [
        ('equals', 'equals'),
        ('before', 'is before'),
        ('after', 'is after'),
        ('between', 'is between'),
        ('in_last_days', 'in the last X days'),
        ('more_than_days_ago', 'more than X days ago'),
        ('is_empty', 'is empty'),
        ('is_not_empty', 'is not empty'),
    ],
    'boolean': [
        ('is_true', 'is true'),
        ('is_false', 'is false'),
    ],
    'select': [
        ('equals', 'equals'),
        ('not_equals', 'does not equal'),
        ('in', 'is one of'),
        ('not_in', 'is not one of'),
    ],
    'tag': [
        ('has_tag', 'has tag'),
        ('not_has_tag', 'does not have tag'),
        ('has_any_tag', 'has any of these tags'),
        ('has_all_tags', 'has all of these tags'),
        ('has_no_tags', 'has no tags'),
    ],
}


class SegmentEvaluator:
    """
    Evaluates segment rules against contacts to build Django QuerySets.
    """

    @staticmethod
    def get_field_definitions():
        """Return all available fields for segmentation."""
        return FIELD_DEFINITIONS

    @staticmethod
    def get_operators_for_field(field: str, organization=None) -> list:
        """
        Return available operators for a given field.

        Custom fields used to get string operators regardless of their declared
        type, so a number custom field could not be compared with `>` and a date
        one could not be compared at all. With the organization in hand the
        declared type decides, the same as for a column.
        """
        if field.startswith('custom.') and organization is not None:
            from apps.contacts.models import CustomField

            name = field[len('custom.'):]
            declared = CustomField.objects.filter(
                organization=organization, name=name,
            ).values_list('field_type', flat=True).first()
            if declared:
                mapped = operator_type(CUSTOM_FIELD_TYPE_MAP.get(declared, declared))
                return OPERATORS_BY_TYPE.get(mapped, OPERATORS_BY_TYPE['string'])
            return OPERATORS_BY_TYPE['string']

        if field.startswith('custom.'):
            return OPERATORS_BY_TYPE['string']

        field_def = FIELD_DEFINITIONS.get(field, {})
        field_type = operator_type(field_def.get('type', 'string'))
        return OPERATORS_BY_TYPE.get(field_type, OPERATORS_BY_TYPE['string'])

    @staticmethod
    def evaluate_segment(segment) -> Q:
        """
        Build a Django Q object from segment rules.
        Returns a Q object that can be used to filter contacts.
        """
        if segment.is_static:
            # For static segments, filter by membership
            return Q(segment_memberships__segment=segment)

        rules = segment.rules or {}
        if not rules or not rules.get('conditions'):
            return Q()  # Empty rules match all contacts

        return SegmentEvaluator.build_query(rules)

    @staticmethod
    def build_query(rules: dict) -> Q:
        """
        Build a Django Q object from rules dictionary.

        Rules structure:
        {
            "match_type": "all" | "any",
            "conditions": [...],
            "groups": [...]
        }
        """
        match_type = rules.get('match_type', 'all')
        conditions = rules.get('conditions', [])
        groups = rules.get('groups', [])

        q_objects = []

        # Process individual conditions
        for condition in conditions:
            q = SegmentEvaluator.evaluate_condition(condition)
            if q is not None:
                q_objects.append(q)

        # Process nested groups
        for group in groups:
            q = SegmentEvaluator.build_query(group)
            if q:
                q_objects.append(q)

        if not q_objects:
            return Q()

        # Combine conditions based on match_type
        if match_type == 'all':
            # AND all conditions
            result = q_objects[0]
            for q in q_objects[1:]:
                result &= q
            return result
        else:
            # OR all conditions
            result = q_objects[0]
            for q in q_objects[1:]:
                result |= q
            return result

    @staticmethod
    def evaluate_condition(condition: dict) -> Q:
        """
        Evaluate a single condition and return a Q object.

        Condition structure:
        {
            "id": "uuid",
            "field": "email",
            "operator": "contains",
            "value": "@gmail.com"
        }
        """
        field = condition.get('field', '')
        operator = condition.get('operator', '')
        value = condition.get('value')

        if not field or not operator:
            return None

        # Handle tag conditions specially
        if field == 'tag':
            return SegmentEvaluator._evaluate_tag_condition(operator, value)

        # Handle custom fields
        if field.startswith('custom.'):
            return SegmentEvaluator._evaluate_custom_field_condition(
                field, operator, value
            )

        # Dispatch on the field's declared type, not on a list of names. The
        # name lists here had to be extended for every new field and silently
        # treated anything they missed as a string — which is how a date field
        # would have been compared alphabetically.
        spec = FIELD_DEFINITIONS.get(field)
        if spec is None:
            # Refused rather than passed to the ORM. An unknown name used to
            # become Q(<name>__iexact=...) and surface as a FieldError 500.
            raise UnknownSegmentField(field)

        kind = operator_type(spec.get('type', 'string'))

        if kind == 'date':
            return SegmentEvaluator._evaluate_date_condition(field, operator, value)
        if kind == 'boolean':
            return SegmentEvaluator._evaluate_boolean_condition(field, operator, value)
        if kind == 'number':
            return SegmentEvaluator._evaluate_number_condition(field, operator, value)
        return SegmentEvaluator._evaluate_string_condition(field, operator, value)

    @staticmethod
    def _evaluate_string_condition(field: str, operator: str, value) -> Q:
        """Evaluate string field conditions."""
        if operator == 'equals':
            return Q(**{f'{field}__iexact': value})
        elif operator == 'not_equals':
            return ~Q(**{f'{field}__iexact': value})
        elif operator == 'contains':
            return Q(**{f'{field}__icontains': value})
        elif operator == 'not_contains':
            return ~Q(**{f'{field}__icontains': value})
        elif operator == 'starts_with':
            return Q(**{f'{field}__istartswith': value})
        elif operator == 'ends_with':
            return Q(**{f'{field}__iendswith': value})
        elif operator == 'is_empty':
            return Q(**{f'{field}__isnull': True}) | Q(**{f'{field}': ''})
        elif operator == 'is_not_empty':
            return ~Q(**{f'{field}__isnull': True}) & ~Q(**{f'{field}': ''})
        elif operator == 'in':
            values = value if isinstance(value, list) else [value]
            return Q(**{f'{field}__in': values})
        elif operator == 'not_in':
            values = value if isinstance(value, list) else [value]
            return ~Q(**{f'{field}__in': values})

        return Q()

    @staticmethod
    def _evaluate_number_condition(field: str, operator: str, value) -> Q:
        """Evaluate number field conditions."""
        try:
            if operator == 'equals':
                return Q(**{field: float(value)})
            elif operator == 'not_equals':
                return ~Q(**{field: float(value)})
            elif operator == 'greater_than':
                return Q(**{f'{field}__gt': float(value)})
            elif operator == 'less_than':
                return Q(**{f'{field}__lt': float(value)})
            elif operator == 'greater_or_equal':
                return Q(**{f'{field}__gte': float(value)})
            elif operator == 'less_or_equal':
                return Q(**{f'{field}__lte': float(value)})
            elif operator == 'between':
                if isinstance(value, list) and len(value) == 2:
                    return Q(**{f'{field}__gte': float(value[0])}) & Q(**{f'{field}__lte': float(value[1])})
            elif operator == 'is_empty':
                return Q(**{f'{field}__isnull': True})
            elif operator == 'is_not_empty':
                return Q(**{f'{field}__isnull': False})
        except (ValueError, TypeError):
            pass

        return Q()

    @staticmethod
    def _evaluate_date_condition(field: str, operator: str, value) -> Q:
        """Evaluate date field conditions."""
        from datetime import datetime

        try:
            if operator == 'equals':
                date_val = datetime.fromisoformat(value.replace('Z', '+00:00')).date()
                return Q(**{f'{field}__date': date_val})
            elif operator == 'before':
                date_val = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return Q(**{f'{field}__lt': date_val})
            elif operator == 'after':
                date_val = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return Q(**{f'{field}__gt': date_val})
            elif operator == 'between':
                if isinstance(value, list) and len(value) == 2:
                    start = datetime.fromisoformat(value[0].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(value[1].replace('Z', '+00:00'))
                    return Q(**{f'{field}__gte': start}) & Q(**{f'{field}__lte': end})
            elif operator == 'in_last_days':
                days = int(value)
                cutoff = timezone.now() - timedelta(days=days)
                return Q(**{f'{field}__gte': cutoff})
            elif operator == 'more_than_days_ago':
                days = int(value)
                cutoff = timezone.now() - timedelta(days=days)
                return Q(**{f'{field}__lt': cutoff})
            elif operator == 'is_empty':
                return Q(**{f'{field}__isnull': True})
            elif operator == 'is_not_empty':
                return Q(**{f'{field}__isnull': False})
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing date condition: {e}")

        return Q()

    @staticmethod
    def _evaluate_boolean_condition(field: str, operator: str, value) -> Q:
        """Evaluate boolean field conditions."""
        if operator == 'is_true':
            return Q(**{field: True})
        elif operator == 'is_false':
            return Q(**{field: False})

        return Q()

    @staticmethod
    def _evaluate_tag_condition(operator: str, value) -> Q:
        """Evaluate tag-based conditions."""
        if operator == 'has_tag':
            # Contact has a specific tag
            return Q(tags__id=value)
        elif operator == 'not_has_tag':
            # Contact does not have a specific tag
            return ~Q(tags__id=value)
        elif operator == 'has_any_tag':
            # Contact has any of the specified tags
            tag_ids = value if isinstance(value, list) else [value]
            return Q(tags__id__in=tag_ids)
        elif operator == 'has_all_tags':
            # Contact has all of the specified tags
            tag_ids = value if isinstance(value, list) else [value]
            q = Q()
            for tag_id in tag_ids:
                q &= Q(tags__id=tag_id)
            return q
        elif operator == 'has_no_tags':
            # Contact has no tags
            return ~Q(tags__isnull=False)

        return Q()

    @staticmethod
    def _evaluate_custom_field_condition(field: str, operator: str, value) -> Q:
        """Evaluate custom field conditions using JSON field lookups."""
        # Extract field name from 'custom.field_name'
        field_name = field.replace('custom.', '')
        json_path = f'custom_fields__{field_name}'

        if operator == 'equals':
            return Q(**{json_path: value})
        elif operator == 'not_equals':
            return ~Q(**{json_path: value})
        elif operator == 'contains':
            return Q(**{f'{json_path}__icontains': value})
        elif operator == 'not_contains':
            return ~Q(**{f'{json_path}__icontains': value})
        elif operator == 'is_empty':
            return Q(**{f'{json_path}__isnull': True}) | Q(**{json_path: ''})
        elif operator == 'is_not_empty':
            return Q(**{f'{json_path}__isnull': False}) & ~Q(**{json_path: ''})

        return Q()

    @staticmethod
    def get_segment_contacts(segment, organization) -> 'QuerySet[Contact]':
        """
        Get all contacts matching a segment's rules.
        """
        base_qs = Contact.objects.filter(organization=organization)

        if segment.is_static:
            # For static segments, return contacts through membership
            return base_qs.filter(segment_memberships__segment=segment)

        # For dynamic segments, apply rules
        q = SegmentEvaluator.evaluate_segment(segment)
        return base_qs.filter(q).distinct()

    @staticmethod
    def count_segment_contacts(segment, organization) -> int:
        """Get the count of contacts matching segment rules."""
        return SegmentEvaluator.get_segment_contacts(segment, organization).count()

    @staticmethod
    def preview_rules(rules: dict, organization) -> 'QuerySet[Contact]':
        """
        Preview contacts matching rules without saving the segment.
        Used for real-time preview in the UI.
        """
        base_qs = Contact.objects.filter(organization=organization)
        q = SegmentEvaluator.build_query(rules)
        return base_qs.filter(q).distinct()

    @staticmethod
    def contact_matches_segment(contact, segment) -> bool:
        """
        Check if a specific contact matches a segment's rules.
        """
        if segment.is_static:
            return segment.memberships.filter(contact=contact).exists()

        q = SegmentEvaluator.evaluate_segment(segment)
        return Contact.objects.filter(Q(id=contact.id) & q).exists()
