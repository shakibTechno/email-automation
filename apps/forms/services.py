"""
Services for the Forms & Lead Capture app.
"""
import csv
import io
import logging

from django.db import transaction
from django.utils import timezone
from apps.contacts.models import Contact, ContactTag

logger = logging.getLogger(__name__)


class FormSubmissionService:
    """Service class for form submission operations."""

    @staticmethod
    def validate_submission_data(form, data):
        """
        Validate submitted data against form field definitions.
        Args:
            form: Form instance (with fields prefetched)
            data: dict of field_id (str) -> value
        Returns:
            list of error strings (empty if valid)
        """
        errors = []
        fields_by_id = {str(f.id): f for f in form.fields.all()}

        # Check required fields
        for field_id, field in fields_by_id.items():
            if field.is_required:
                value = data.get(field_id)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(f"'{field.label}' is required.")

        # Check that submitted field IDs exist in the form
        for field_id in data.keys():
            if field_id not in fields_by_id:
                errors.append(f"Unknown field: {field_id}")

        return errors

    @staticmethod
    @transaction.atomic
    def process_submission(form, data, ip_address=None, user_agent='', source_url=''):
        """
        Process a form submission:
        1. Build submission data array with labels
        2. Create FormSubmission record
        3. Upsert Contact based on field mappings
        4. Assign tags
        5. Increment submission count
        """
        from .models import FormSubmission

        fields_by_id = {str(f.id): f for f in form.fields.all()}

        # Build submission data array with labels for historical accuracy
        submission_data = []
        for field_id, value in data.items():
            field = fields_by_id.get(field_id)
            if field:
                submission_data.append({
                    'field_id': field_id,
                    'label': field.label,
                    'field_type': field.field_type,
                    'value': value,
                })

        # Upsert contact FIRST (before creating submission)
        # This ensures contact is linked when submission is created,
        # allowing workflow signals to fire correctly
        contact = FormSubmissionService.upsert_contact(
            organization=form.organization,
            fields_by_id=fields_by_id,
            submitted_data=data,
        )

        # Create submission record WITH contact linked
        submission = FormSubmission.objects.create(
            form=form,
            contact=contact,  # Link contact at creation time for signals
            data=submission_data,
            ip_address=ip_address,
            user_agent=user_agent,
            source_url=source_url,
        )

        # If contact exists, assign tags and update activity
        if contact:
            # Assign tags from form.assign_tags
            tag_ids = list(form.assign_tags.values_list('id', flat=True))
            for tag_id in tag_ids:
                ContactTag.objects.get_or_create(
                    contact=contact,
                    tag_id=tag_id,
                )

            # Update contact source and activity
            if contact.source == 'manual':
                contact.source = 'form'
                contact.save(update_fields=['source'])
            contact.update_activity()

        # Increment submission count
        form.submission_count = (form.submission_count or 0) + 1
        form.save(update_fields=['submission_count'])

        return submission

    @staticmethod
    def upsert_contact(organization, fields_by_id, submitted_data):
        """
        Find or create a Contact based on field mappings.
        Returns Contact instance or None if no email mapping found.
        """
        # Build mapping: contact_field -> submitted value
        mapped_values = {}
        for field_id, value in submitted_data.items():
            field = fields_by_id.get(field_id)
            if field and field.contact_field_mapping:
                mapped_values[field.contact_field_mapping] = value

        email = mapped_values.get('email')
        if not email:
            return None

        # Try to find existing contact by email in the organization
        try:
            contact = Contact.objects.get(
                organization=organization,
                email=email,
            )
            # Update mapped fields
            updated_fields = []
            for field_name, value in mapped_values.items():
                if field_name == 'email':
                    continue
                if value and hasattr(contact, field_name):
                    setattr(contact, field_name, value)
                    updated_fields.append(field_name)
            if updated_fields:
                contact.save(update_fields=updated_fields)
            return contact
        except Contact.DoesNotExist:
            # Create new contact
            create_kwargs = {
                'organization': organization,
                'email': email,
                'source': 'form',
            }
            for field_name, value in mapped_values.items():
                if field_name == 'email':
                    continue
                if value:
                    create_kwargs[field_name] = value
            return Contact.objects.create(**create_kwargs)


class FormExportService:
    """Service class for exporting form submissions."""

    @staticmethod
    def export_submissions_csv(form):
        """
        Export all submissions for a form as CSV string.
        Returns CSV content as a string.
        """
        submissions = form.submissions.all().select_related('contact').order_by('created_at')
        fields = form.fields.all().order_by('order', 'created_at')

        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        headers = [f.label for f in fields]
        headers.extend(['Submitted At', 'IP Address', 'Contact Email', 'GDPR Consent'])
        writer.writerow(headers)

        # Data rows
        field_ids = [str(f.id) for f in fields]
        for submission in submissions:
            # Build lookup from submission data
            data_lookup = {}
            for item in submission.data:
                data_lookup[item.get('field_id', '')] = item.get('value', '')

            row = [data_lookup.get(fid, '') for fid in field_ids]
            row.append(submission.created_at.strftime('%Y-%m-%d %H:%M:%S') if submission.created_at else '')
            row.append(submission.ip_address or '')
            row.append(submission.contact.email if submission.contact else '')
            row.append('Yes' if submission.gdpr_consent_given else 'No')
            writer.writerow(row)

        return output.getvalue()
