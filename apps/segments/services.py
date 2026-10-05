"""
Services for the Contact Segmentation app.
"""
import logging
from typing import List, Optional
from django.db import transaction
from django.utils import timezone
from django.db.models import QuerySet

from apps.contacts.models import Contact
from .models import Segment, SegmentMembership
from .evaluator import SegmentEvaluator

logger = logging.getLogger(__name__)


class SegmentService:
    """Service class for segment operations."""

    @staticmethod
    @transaction.atomic
    def create_segment(
        organization,
        name: str,
        segment_type: str = 'dynamic',
        description: str = '',
        rules: dict = None,
        created_by=None
    ) -> Segment:
        """
        Create a new segment.

        Args:
            organization: Organization instance
            name: Segment name
            segment_type: 'static' or 'dynamic'
            description: Optional description
            rules: Rules dict for dynamic segments
            created_by: User who created the segment

        Returns:
            Created Segment instance
        """
        segment = Segment.objects.create(
            organization=organization,
            name=name,
            segment_type=segment_type,
            description=description,
            rules=rules or {},
            created_by=created_by,
        )

        # Calculate initial contact count for dynamic segments
        if segment.is_dynamic and rules:
            SegmentService.refresh_segment_count(segment)

        return segment

    @staticmethod
    @transaction.atomic
    def update_segment(
        segment: Segment,
        name: str = None,
        description: str = None,
        rules: dict = None
    ) -> Segment:
        """
        Update segment details.

        Args:
            segment: Segment instance to update
            name: New name (optional)
            description: New description (optional)
            rules: New rules for dynamic segments (optional)

        Returns:
            Updated Segment instance
        """
        update_fields = []

        if name is not None:
            segment.name = name
            update_fields.append('name')

        if description is not None:
            segment.description = description
            update_fields.append('description')

        if rules is not None and segment.is_dynamic:
            segment.rules = rules
            update_fields.append('rules')

        if update_fields:
            segment.save(update_fields=update_fields)

        # Refresh count if rules changed
        if 'rules' in update_fields:
            SegmentService.refresh_segment_count(segment)

        return segment

    @staticmethod
    def refresh_segment_count(segment: Segment) -> int:
        """
        Refresh the cached contact count for a segment.

        Args:
            segment: Segment instance

        Returns:
            New contact count
        """
        count = SegmentEvaluator.count_segment_contacts(segment, segment.organization)
        segment.contact_count = count
        segment.last_calculated_at = timezone.now()
        segment.save(update_fields=['contact_count', 'last_calculated_at'])
        return count

    @staticmethod
    def get_segment_contacts(segment: Segment) -> QuerySet:
        """
        Get all contacts matching a segment.

        Args:
            segment: Segment instance

        Returns:
            QuerySet of Contact instances
        """
        return SegmentEvaluator.get_segment_contacts(segment, segment.organization)

    @staticmethod
    def preview_rules(organization, rules: dict, limit: int = 100) -> dict:
        """
        Preview contacts matching rules without saving.

        Args:
            organization: Organization instance
            rules: Rules dict to evaluate
            limit: Max contacts to return

        Returns:
            Dict with count and sample contacts
        """
        contacts_qs = SegmentEvaluator.preview_rules(rules, organization)
        total_count = contacts_qs.count()

        # Get sample contacts
        sample_contacts = list(
            contacts_qs[:limit].values('id', 'email', 'first_name', 'last_name')
        )

        return {
            'total_count': total_count,
            'sample_contacts': sample_contacts,
            'has_more': total_count > limit,
        }

    # -------------------------
    # Static Segment Operations
    # -------------------------

    @staticmethod
    @transaction.atomic
    def add_contacts_to_segment(
        segment: Segment,
        contact_ids: List[str],
        added_by=None
    ) -> dict:
        """
        Add contacts to a static segment.

        Args:
            segment: Static Segment instance
            contact_ids: List of contact UUIDs to add
            added_by: User who added the contacts

        Returns:
            Dict with added and already_member counts
        """
        if not segment.is_static:
            raise ValueError("Cannot manually add contacts to a dynamic segment")

        # Get contacts that belong to the organization
        contacts = Contact.objects.filter(
            id__in=contact_ids,
            organization=segment.organization
        )

        added_count = 0
        already_member_count = 0

        for contact in contacts:
            membership, created = SegmentMembership.objects.get_or_create(
                segment=segment,
                contact=contact,
                defaults={'added_by': added_by}
            )
            if created:
                added_count += 1
            else:
                already_member_count += 1

        # Update contact count
        segment.contact_count = segment.memberships.count()
        segment.last_calculated_at = timezone.now()
        segment.save(update_fields=['contact_count', 'last_calculated_at'])

        return {
            'added': added_count,
            'already_member': already_member_count,
        }

    @staticmethod
    @transaction.atomic
    def remove_contacts_from_segment(
        segment: Segment,
        contact_ids: List[str]
    ) -> int:
        """
        Remove contacts from a static segment.

        Args:
            segment: Static Segment instance
            contact_ids: List of contact UUIDs to remove

        Returns:
            Number of contacts removed
        """
        if not segment.is_static:
            raise ValueError("Cannot manually remove contacts from a dynamic segment")

        deleted_count, _ = SegmentMembership.objects.filter(
            segment=segment,
            contact_id__in=contact_ids
        ).delete()

        # Update contact count
        segment.contact_count = segment.memberships.count()
        segment.last_calculated_at = timezone.now()
        segment.save(update_fields=['contact_count', 'last_calculated_at'])

        return deleted_count

    @staticmethod
    def contact_is_in_segment(segment: Segment, contact: Contact) -> bool:
        """
        Check if a contact is in a segment.

        Args:
            segment: Segment instance
            contact: Contact instance

        Returns:
            True if contact matches segment
        """
        return SegmentEvaluator.contact_matches_segment(contact, segment)

    # -------------------------
    # Export Operations
    # -------------------------

    @staticmethod
    def export_segment_contacts_csv(segment: Segment) -> str:
        """
        Export segment contacts as CSV string.

        Args:
            segment: Segment instance

        Returns:
            CSV content as string
        """
        import csv
        import io

        contacts = SegmentService.get_segment_contacts(segment)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        headers = [
            'Email', 'First Name', 'Last Name', 'Company', 'Job Title',
            'Phone', 'Engagement Level', 'Source', 'Lead Score', 'Subscribed', 'Created At'
        ]
        writer.writerow(headers)

        # Data rows
        for contact in contacts:
            row = [
                contact.email,
                contact.first_name or '',
                contact.last_name or '',
                contact.company or '',
                contact.job_title or '',
                contact.phone or '',
                contact.engagement_level,
                contact.source,
                contact.lead_score or 0,
                'Yes' if contact.is_subscribed else 'No',
                contact.created_at.strftime('%Y-%m-%d %H:%M:%S') if contact.created_at else '',
            ]
            writer.writerow(row)

        return output.getvalue()

    # -------------------------
    # Validation
    # -------------------------

    @staticmethod
    def validate_rules(rules: dict) -> List[str]:
        """
        Validate segment rules structure.

        Args:
            rules: Rules dict to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not isinstance(rules, dict):
            errors.append("Rules must be a dictionary")
            return errors

        # Check match_type
        match_type = rules.get('match_type', 'all')
        if match_type not in ('all', 'any'):
            errors.append("match_type must be 'all' or 'any'")

        conditions = rules.get('conditions', [])
        groups = rules.get('groups', [])

        # Must have at least one condition or group
        if not conditions and not groups:
            errors.append("Segment must have at least one condition or group")

        # Validate each condition
        for i, condition in enumerate(conditions):
            cond_errors = SegmentService._validate_condition(condition, i)
            errors.extend(cond_errors)

        # Validate nested groups recursively
        for i, group in enumerate(groups):
            group_errors = SegmentService.validate_rules(group)
            for err in group_errors:
                errors.append(f"Group {i + 1}: {err}")

        return errors

    @staticmethod
    def _validate_condition(condition: dict, index: int) -> List[str]:
        """Validate a single condition."""
        errors = []
        prefix = f"Condition {index + 1}"

        if not isinstance(condition, dict):
            errors.append(f"{prefix}: must be a dictionary")
            return errors

        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')

        if not field:
            errors.append(f"{prefix}: field is required")

        if not operator:
            errors.append(f"{prefix}: operator is required")

        # Check if operator is valid for field type
        if field and operator:
            valid_operators = SegmentEvaluator.get_operators_for_field(field)
            valid_op_codes = [op[0] for op in valid_operators]
            if operator not in valid_op_codes:
                errors.append(f"{prefix}: invalid operator '{operator}' for field '{field}'")

        # Check value requirements
        if operator and operator not in ('is_empty', 'is_not_empty', 'is_true', 'is_false', 'has_no_tags'):
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"{prefix}: value is required for operator '{operator}'")

        return errors

    # -------------------------
    # Bulk Operations
    # -------------------------

    @staticmethod
    @transaction.atomic
    def refresh_all_segment_counts(organization) -> int:
        """
        Refresh contact counts for all segments in an organization.

        Args:
            organization: Organization instance

        Returns:
            Number of segments refreshed
        """
        segments = Segment.objects.filter(organization=organization)
        count = 0

        for segment in segments:
            SegmentService.refresh_segment_count(segment)
            count += 1

        return count

    @staticmethod
    def duplicate_segment(segment: Segment, user=None) -> Segment:
        """
        Duplicate a segment.

        Args:
            segment: Segment to duplicate
            user: User creating the duplicate

        Returns:
            New Segment instance
        """
        new_segment = SegmentService.create_segment(
            organization=segment.organization,
            name=f"{segment.name} (Copy)",
            segment_type=segment.segment_type,
            description=segment.description,
            rules=segment.rules.copy() if segment.rules else None,
            created_by=user,
        )

        # For static segments, also copy memberships
        if segment.is_static:
            memberships = segment.memberships.all()
            new_memberships = [
                SegmentMembership(
                    segment=new_segment,
                    contact=m.contact,
                    added_by=user,
                )
                for m in memberships
            ]
            SegmentMembership.objects.bulk_create(new_memberships)

            # Update count
            new_segment.contact_count = len(new_memberships)
            new_segment.save(update_fields=['contact_count'])

        return new_segment
