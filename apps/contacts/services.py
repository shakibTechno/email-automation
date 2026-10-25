"""
Service layer for contact operations.
"""
import csv
import io
from typing import Dict, List, Tuple
from django.db import transaction
from django.utils import timezone
from .models import Contact, ContactTag, Tag
from . import fields as contact_fields
from .custom_fields import CustomFieldError, CustomFieldService
import logging

logger = logging.getLogger(__name__)


class CSVExportService:
    """Service for exporting contacts to CSV."""

    DEFAULT_FIELDS = [
        'email', 'first_name', 'last_name', 'phone',
        'company', 'job_title', 'lead_score',
        'engagement_level', 'status', 'is_subscribed', 'is_verified',
        'city', 'country', 'lifecycle_stage',
        'source', 'created_at', 'last_activity_at'
    ]

    @staticmethod
    def export_contacts(contacts_queryset, fields=None):
        """
        Export contacts to CSV.

        Args:
            contacts_queryset: QuerySet of contacts to export
            fields: List of fields to include (default: DEFAULT_FIELDS)

        Returns:
            CSV content as string
        """
        if fields is None:
            fields = CSVExportService.DEFAULT_FIELDS
        else:
            # getattr() below would otherwise read any attribute the
            # caller names, including internals that are not the
            # customer's to export.
            allowed = contact_fields.exportable_keys()
            fields = [f for f in fields if f in allowed]
            if not fields:
                fields = CSVExportService.DEFAULT_FIELDS

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()

        for contact in contacts_queryset:
            row = {}
            for field in fields:
                value = getattr(contact, field, '')

                # Handle datetime fields
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()

                # Handle boolean fields
                elif isinstance(value, bool):
                    value = 'Yes' if value else 'No'

                row[field] = value

            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def export_contacts_with_tags(contacts_queryset):
        """
        Export contacts with their tags to CSV.

        Args:
            contacts_queryset: QuerySet of contacts to export

        Returns:
            CSV content as string
        """
        fields = CSVExportService.DEFAULT_FIELDS + ['tags']
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()

        for contact in contacts_queryset.prefetch_related('contact_tags__tag'):
            row = {}
            for field in CSVExportService.DEFAULT_FIELDS:
                value = getattr(contact, field, '')

                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif isinstance(value, bool):
                    value = 'Yes' if value else 'No'

                row[field] = value

            # Add tags
            tags = [ct.tag.name for ct in contact.contact_tags.all()]
            row['tags'] = ', '.join(tags)

            writer.writerow(row)

        return output.getvalue()


class CSVImportService:
    """Service for importing contacts from CSV."""

    DEFAULT_FIELD_MAPPING = {
        'email': 'email',
        'first_name': 'first_name',
        'last_name': 'last_name',
        'phone': 'phone',
        'company': 'company',
        'job_title': 'job_title',
    }

    def __init__(self, organization, user):
        self.organization = organization
        self.user = user
        self.errors = []
        self.imported_count = 0
        self.updated_count = 0
        self.skipped_count = 0

    def import_from_csv(
        self,
        csv_file,
        field_mapping: Dict[str, str] = None,
        skip_duplicates: bool = True,
        update_existing: bool = False
    ) -> Dict:
        """
        Import contacts from CSV file.

        Args:
            csv_file: CSV file object
            field_mapping: Mapping of CSV columns to Contact fields
            skip_duplicates: Skip duplicate emails
            update_existing: Update existing contacts

        Returns:
            Dictionary with import statistics
        """
        if field_mapping is None:
            field_mapping = self.DEFAULT_FIELD_MAPPING

        try:
            # Read CSV file
            csv_content = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_content))

            # Validate headers
            self._validate_headers(csv_reader.fieldnames, field_mapping)

            # Process rows
            with transaction.atomic():
                for row_number, row in enumerate(csv_reader, start=2):
                    self._process_row(
                        row, row_number, field_mapping,
                        skip_duplicates, update_existing
                    )

        except Exception as e:
            logger.error(f"CSV import error: {str(e)}")
            self.errors.append({
                'row': 0,
                'error': f"File processing error: {str(e)}"
            })

        return {
            'imported': self.imported_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': self.errors
        }

    def _validate_headers(self, headers, field_mapping):
        """Validate CSV headers."""
        if not headers:
            raise ValueError("CSV file is empty or has no headers")

        # Check if required model fields are mapped
        required_model_fields = ['email']
        mapped_model_fields = [str(v) for v in field_mapping.values()]

        for field in required_model_fields:
            if field not in mapped_model_fields:
                raise ValueError(f"Required field '{field}' must be mapped in field_mapping")

    def _process_row(
        self, row, row_number, field_mapping,
        skip_duplicates, update_existing
    ):
        """Process a single CSV row."""
        try:
            # Map CSV columns to Contact fields.
            #
            # Through the registry, never straight onto the model. This loop
            # used to do `contact_data[model_field] = value` with whatever
            # target name the request supplied, so a mapping of
            # {"col": "organization_id"} wrote the contact into another
            # tenant's organization. The serializer now rejects such a mapping
            # up front; this stays defensive because it is the line that would
            # do the damage.
            contact_data = {}
            custom_data = {}
            for csv_column, target in field_mapping.items():
                if csv_column not in row:
                    continue
                raw = (row[csv_column] or '').strip()
                if not raw:
                    continue

                if contact_fields.is_custom_target(target):
                    custom_data[contact_fields.custom_key(target)] = raw
                    continue

                reason = contact_fields.rejection_reason(target, contact_fields.IMPORT)
                if reason:
                    raise ValueError(reason)
                contact_data[target] = contact_fields.coerce(target, raw)

            # Validate email
            if 'email' not in contact_data or not contact_data['email']:
                self.errors.append({
                    'row': row_number,
                    'error': 'Email is required'
                })
                self.skipped_count += 1
                return

            email = contact_data['email']

            # Check for duplicates
            existing_contact = Contact.objects.filter(
                organization=self.organization,
                email=email
            ).first()

            if existing_contact:
                if update_existing:
                    # Update existing contact
                    for field, value in contact_data.items():
                        if field != 'email':  # Don't update email
                            setattr(existing_contact, field, value)
                    if custom_data:
                        # Merged, not replaced: a CSV with one custom column
                        # must not wipe the others this contact already has.
                        # Validated against the definitions too, so an import
                        # cannot write a field nobody declared or a value of
                        # the wrong type.
                        existing_contact.custom_fields = CustomFieldService.merge(
                            self.organization,
                            existing_contact.custom_fields,
                            custom_data,
                        )
                    existing_contact.save()
                    self.updated_count += 1
                elif skip_duplicates:
                    self.skipped_count += 1
                else:
                    self.errors.append({
                        'row': row_number,
                        'error': f'Duplicate email: {email}'
                    })
                    self.skipped_count += 1
            else:
                # Create new contact
                # Set last, so no mapping can override either: the
                # organization is whose import this is, and the source is how
                # the contact arrived.
                contact_data['organization'] = self.organization
                contact_data['source'] = 'import'
                if custom_data:
                    contact_data['custom_fields'] = (
                        CustomFieldService.validate_and_coerce(
                            self.organization, custom_data,
                        )
                    )
                Contact.objects.create(**contact_data)
                self.imported_count += 1

        except CustomFieldError as e:
            # Reported per row with the offending field named, rather than
            # failing the whole file: one bad cell in row 400 should not
            # discard the 399 rows that were fine.
            self.errors.append({'row': row_number, 'error': str(e)})
            self.skipped_count += 1
        except Exception as e:
            logger.error(f"Error processing row {row_number}: {str(e)}")
            self.errors.append({
                'row': row_number,
                'error': str(e)
            })
            self.skipped_count += 1


class ActivityTimelineService:
    """
    Aggregates activity events from all sources for a single contact,
    merges and sorts them by timestamp descending.
    """

    @staticmethod
    def get_timeline(contact, limit: int = 20, offset: int = 0) -> dict:
        events = []

        # --- Email events from CampaignRecipient ---
        from apps.campaigns.models import CampaignRecipient
        recipients = (
            CampaignRecipient.objects
            .filter(contact=contact)
            .select_related('campaign')
        )
        for r in recipients:
            meta = {
                'campaign_id': str(r.campaign_id),
                'campaign_name': r.campaign.name,
            }
            if r.sent_at:
                events.append({
                    'id': f'email_sent_{r.id}',
                    'type': 'email_sent',
                    'title': r.campaign.name,
                    'description': 'Campaign email delivered',
                    'timestamp': r.sent_at,
                    'metadata': meta,
                })
            if r.opened_at:
                events.append({
                    'id': f'email_opened_{r.id}',
                    'type': 'email_opened',
                    'title': r.campaign.name,
                    'description': 'Opened email',
                    'timestamp': r.opened_at,
                    'metadata': meta,
                })
            if r.clicked_at:
                events.append({
                    'id': f'email_clicked_{r.id}',
                    'type': 'email_clicked',
                    'title': r.campaign.name,
                    'description': 'Clicked a link in email',
                    'timestamp': r.clicked_at,
                    'metadata': meta,
                })
            if r.bounced_at:
                events.append({
                    'id': f'email_bounced_{r.id}',
                    'type': 'email_bounced',
                    'title': r.campaign.name,
                    'description': 'Email bounced',
                    'timestamp': r.bounced_at,
                    'metadata': meta,
                })
            if r.unsubscribed_at:
                events.append({
                    'id': f'email_unsubscribed_{r.id}',
                    'type': 'email_unsubscribed',
                    'title': r.campaign.name,
                    'description': 'Unsubscribed via email',
                    'timestamp': r.unsubscribed_at,
                    'metadata': meta,
                })

        # --- Form submissions ---
        from apps.forms.models import FormSubmission
        for s in FormSubmission.objects.filter(contact=contact).select_related('form'):
            events.append({
                'id': f'form_submission_{s.id}',
                'type': 'form_submission',
                'title': s.form.name,
                'description': 'Submitted a form',
                'timestamp': s.created_at,
                'metadata': {
                    'form_id': str(s.form_id),
                    'form_name': s.form.name,
                    'source_url': s.source_url or '',
                },
            })

        # --- Workflow executions ---
        from apps.workflows.models import WorkflowExecution
        for e in WorkflowExecution.objects.filter(contact=contact).select_related('workflow'):
            meta = {
                'workflow_id': str(e.workflow_id),
                'workflow_name': e.workflow.name,
            }
            events.append({
                'id': f'workflow_started_{e.id}',
                'type': 'workflow_started',
                'title': e.workflow.name,
                'description': 'Entered workflow',
                'timestamp': e.started_at or e.created_at,
                'metadata': meta,
            })
            if e.completed_at:
                label = 'Completed workflow (goal reached)' if e.goal_reached else 'Completed workflow'
                events.append({
                    'id': f'workflow_completed_{e.id}',
                    'type': 'workflow_completed',
                    'title': e.workflow.name,
                    'description': label,
                    'timestamp': e.completed_at,
                    'metadata': {**meta, 'goal_reached': e.goal_reached},
                })

        # --- CRM Activities ---
        from apps.crm.models import Activity
        for a in Activity.objects.filter(contact=contact).select_related('created_by'):
            by = ''
            if a.created_by:
                by = f'{a.created_by.first_name} {a.created_by.last_name}'.strip()
            events.append({
                'id': f'crm_{a.id}',
                'type': f'crm_{a.activity_type}',
                'title': a.title,
                'description': a.description or '',
                'timestamp': a.created_at,
                'metadata': {
                    'activity_type': a.activity_type,
                    'is_completed': a.is_completed,
                    'created_by': by,
                },
            })

        # --- Lead score changes ---
        from apps.lead_scoring.models import ScoreHistory
        for h in ScoreHistory.objects.filter(contact=contact).select_related('rule'):
            if h.reason == ScoreHistory.REASON_MANUAL:
                title = 'Manual score adjustment'
            elif h.reason == ScoreHistory.REASON_RECALC:
                title = 'Score recalculation'
            else:
                title = h.rule.name if h.rule else 'Scoring rule triggered'
            events.append({
                'id': f'score_{h.id}',
                'type': 'score_change',
                'title': title,
                'description': h.note or '',
                'timestamp': h.created_at,
                'metadata': {
                    'reason': h.reason,
                    'points_delta': h.points_delta,
                    'score_before': h.score_before,
                    'score_after': h.score_after,
                },
            })

        # Sort by timestamp descending (None timestamps go last)
        events.sort(key=lambda x: x['timestamp'] or timezone.datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        total = len(events)
        paginated = events[offset: offset + limit]

        for event in paginated:
            ts = event['timestamp']
            event['timestamp'] = ts.isoformat() if ts else None

        return {'count': total, 'results': paginated}


class DuplicateDetectionService:
    """Service for detecting and handling duplicate contacts."""

    @staticmethod
    def find_duplicates_by_email(organization) -> List[List[Contact]]:
        """
        Find contacts with duplicate emails within an organization.

        Args:
            organization: Organization to search within

        Returns:
            List of lists, where each inner list contains duplicate contacts
        """
        from django.db.models import Count

        # Find duplicate emails
        duplicate_emails = (
            Contact.objects.filter(organization=organization)
            .values('email')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .values_list('email', flat=True)
        )

        # Group contacts by duplicate email
        duplicate_groups = []
        for email in duplicate_emails:
            contacts = list(
                Contact.objects.filter(
                    organization=organization,
                    email=email
                ).order_by('-created_at')
            )
            duplicate_groups.append(contacts)

        return duplicate_groups

    @staticmethod
    def find_similar_contacts(
        organization,
        email: str = None,
        first_name: str = None,
        last_name: str = None
    ) -> List[Contact]:
        """
        Find contacts that are similar based on provided criteria.

        Args:
            organization: Organization to search within
            email: Email to search for
            first_name: First name to search for
            last_name: Last name to search for

        Returns:
            List of similar contacts
        """
        queryset = Contact.objects.filter(organization=organization)

        if email:
            queryset = queryset.filter(email__iexact=email)

        if first_name and last_name:
            queryset = queryset.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            )

        return list(queryset)

    @staticmethod
    @transaction.atomic
    def merge_contacts(
        primary_contact: Contact,
        duplicate_contacts: List[Contact]
    ) -> Contact:
        """
        Merge duplicate contacts into a primary contact.

        Args:
            primary_contact: The contact to keep
            duplicate_contacts: List of contacts to merge

        Returns:
            The merged primary contact
        """
        for duplicate in duplicate_contacts:
            # Don't merge the contact with itself
            if duplicate.id == primary_contact.id:
                continue

            # Merge custom fields
            for key, value in duplicate.custom_fields.items():
                if key not in primary_contact.custom_fields:
                    primary_contact.custom_fields[key] = value

            # Merge tags
            for contact_tag in duplicate.contact_tags.all():
                ContactTag.objects.get_or_create(
                    contact=primary_contact,
                    tag=contact_tag.tag
                )

            # Update engagement metrics if duplicate has better values
            if duplicate.lead_score > primary_contact.lead_score:
                primary_contact.lead_score = duplicate.lead_score

            # Update last activity if duplicate is more recent
            if duplicate.last_activity_at:
                if not primary_contact.last_activity_at or \
                   duplicate.last_activity_at > primary_contact.last_activity_at:
                    primary_contact.last_activity_at = duplicate.last_activity_at

            # Soft delete the duplicate
            duplicate.soft_delete()

        primary_contact.save()
        return primary_contact


class ActivityTimelineService:
    """
    Aggregates activity events from multiple sources into a unified timeline for a contact.
    """

    @staticmethod
    def get_timeline(contact, limit=20, offset=0):
        events = []

        # --- Campaign emails ---
        try:
            from apps.campaigns.models import CampaignRecipient
            recipients = CampaignRecipient.objects.filter(contact=contact).select_related('campaign')
            for r in recipients:
                if r.sent_at:
                    events.append({
                        'type': 'email_sent',
                        'title': f'Email sent: {r.campaign.name}',
                        'description': r.campaign.subject or '',
                        'timestamp': r.sent_at,
                        'meta': {'campaign_id': str(r.campaign.id), 'campaign_name': r.campaign.name},
                    })
                if r.opened_at:
                    events.append({
                        'type': 'email_opened',
                        'title': f'Email opened: {r.campaign.name}',
                        'description': r.campaign.subject or '',
                        'timestamp': r.opened_at,
                        'meta': {'campaign_id': str(r.campaign.id)},
                    })
                if r.clicked_at:
                    events.append({
                        'type': 'email_clicked',
                        'title': f'Email clicked: {r.campaign.name}',
                        'description': '',
                        'timestamp': r.clicked_at,
                        'meta': {'campaign_id': str(r.campaign.id)},
                    })
                if r.unsubscribed_at:
                    events.append({
                        'type': 'unsubscribed',
                        'title': 'Unsubscribed',
                        'description': f'Unsubscribed via {r.campaign.name}',
                        'timestamp': r.unsubscribed_at,
                        'meta': {'campaign_id': str(r.campaign.id)},
                    })
        except Exception:
            pass

        # --- Form submissions ---
        try:
            from apps.forms.models import FormSubmission
            subs = FormSubmission.objects.filter(contact=contact).select_related('form')
            for sub in subs:
                events.append({
                    'type': 'form_submission',
                    'title': f'Form submitted: {sub.form.name}',
                    'description': '',
                    'timestamp': sub.submitted_at if hasattr(sub, 'submitted_at') else sub.created_at,
                    'meta': {'form_id': str(sub.form.id), 'form_name': sub.form.name},
                })
        except Exception:
            pass

        # --- Workflow executions ---
        try:
            from apps.workflows.models import WorkflowExecution
            execs = WorkflowExecution.objects.filter(contact=contact).select_related('workflow')
            for ex in execs:
                label = {
                    'active': 'Workflow started',
                    'completed': 'Workflow completed',
                    'failed': 'Workflow failed',
                    'cancelled': 'Workflow cancelled',
                }.get(ex.status, 'Workflow')
                events.append({
                    'type': f'workflow_{ex.status}',
                    'title': f'{label}: {ex.workflow.name}',
                    'description': '',
                    'timestamp': ex.created_at,
                    'meta': {'workflow_id': str(ex.workflow.id), 'workflow_name': ex.workflow.name, 'status': ex.status},
                })
        except Exception:
            pass

        # --- CRM activities ---
        try:
            from apps.crm.models import Activity
            acts = Activity.objects.filter(contact=contact).select_related('deal', 'created_by')
            for act in acts:
                events.append({
                    'type': f'crm_{act.activity_type}',
                    'title': f'{act.get_activity_type_display()}: {act.subject}',
                    'description': act.notes or '',
                    'timestamp': act.created_at,
                    'meta': {
                        'activity_id': str(act.id),
                        'deal_id': str(act.deal.id) if act.deal else None,
                        'deal_name': act.deal.title if act.deal else None,
                    },
                })
        except Exception:
            pass

        # --- Sequence emails ---
        try:
            from apps.sequences.models import SequenceStepExecution
            seq_execs = SequenceStepExecution.objects.filter(
                enrollment__contact=contact,
                status='sent',
            ).select_related('step__sequence', 'enrollment__sequence')
            for se in seq_execs:
                events.append({
                    'type': 'sequence_email_sent',
                    'title': f'Sequence email sent: {se.step.subject}',
                    'description': f'From sequence: {se.enrollment.sequence.name}',
                    'timestamp': se.sent_at or se.scheduled_at,
                    'meta': {
                        'sequence_id': str(se.enrollment.sequence.id),
                        'sequence_name': se.enrollment.sequence.name,
                        'step_position': se.step.position,
                    },
                })
        except Exception:
            pass

        # --- Tag additions (from ContactTag created_at) ---
        try:
            tags = ContactTag.objects.filter(contact=contact).select_related('tag')
            for ct in tags:
                events.append({
                    'type': 'tag_added',
                    'title': f'Tag added: {ct.tag.name}',
                    'description': '',
                    'timestamp': ct.created_at,
                    'meta': {'tag_id': str(ct.tag.id), 'tag_name': ct.tag.name},
                })
        except Exception:
            pass

        # Sort by timestamp descending, handle None timestamps
        events = [e for e in events if e.get('timestamp')]
        events.sort(key=lambda e: e['timestamp'], reverse=True)

        total = len(events)
        paginated = events[offset:offset + limit]

        # Normalise to match frontend TimelineResponse {count, results}
        results = []
        for i, e in enumerate(paginated):
            ts = e['timestamp']
            if hasattr(ts, 'isoformat'):
                ts = ts.isoformat()
            meta = e.get('meta', e.get('metadata', {}))
            results.append({
                'id': f"{e['type']}-{ts}-{offset + i}",
                'type': e['type'],
                'title': e['title'],
                'description': e.get('description', ''),
                'timestamp': ts,
                'metadata': meta,
            })

        return {
            'count': total,
            'results': results,
        }
