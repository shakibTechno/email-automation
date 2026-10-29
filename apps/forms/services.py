"""
Services for the Forms & Lead Capture app.
"""
import csv
import io
import logging

from django.db import transaction
from django.utils import timezone
from apps.contacts import fields as contact_fields
from apps.contacts.custom_fields import CustomFieldError, CustomFieldService
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
    def contact_field_options(organization):
        """
        What a form field may be mapped to.

        Standard columns come from the contact field registry and custom fields
        from the organization's own definitions, so this grows when either does.
        The builder used to hold its own list of six, which is why a form could
        not capture anything added to the contact since.
        """
        options = [
            {'value': key, 'label': label, 'group': 'Contact fields'}
            for key, label in contact_fields.writable_choices(contact_fields.FORM)
        ]
        options += [
            {
                'value': f'{contact_fields.CUSTOM_PREFIX}{definition.key}',
                'label': definition.name,
                'group': 'Custom fields',
            }
            for definition in CustomFieldService.definitions(organization).values()
        ]
        return options

    @staticmethod
    def upsert_contact(organization, fields_by_id, submitted_data):
        """
        Find or create a Contact from the field mappings.

        Returns the Contact, or None when nothing maps to an email address --
        without one there is no way to tell two submissions apart, so the
        answers stay on the submission alone.

        Targets come in two shapes. A plain key names a column and is coerced
        by the registry; a `custom.` key names one of the organization's own
        fields and is validated against its definition. Anything mapped to
        neither is kept on the submission and surfaced on the contact's
        timeline instead.
        """
        standard = {}
        custom = {}
        for field_id, value in submitted_data.items():
            field = fields_by_id.get(field_id)
            target = field.contact_field_mapping if field else ''
            if not target or value in (None, ''):
                continue

            if contact_fields.is_custom_target(target):
                custom[contact_fields.custom_key(target)] = value
                continue

            # Defensive, like the importer's: this is the line that would do
            # the damage if a mapping ever named something it should not.
            if contact_fields.rejection_reason(target, contact_fields.FORM):
                logger.warning(
                    'Form field mapped to %r, which a form may not write; ignoring.',
                    target,
                )
                continue
            standard[target] = contact_fields.coerce(target, value)

        email = standard.get('email')
        if not email:
            return None

        if custom:
            try:
                custom = CustomFieldService.validate_and_coerce(organization, custom)
            except CustomFieldError as exc:
                # One bad answer must not cost the whole lead. The submission
                # keeps every answer either way.
                logger.warning(
                    'Dropping custom field values from a form submission: %s', exc,
                )
                custom = {}

        contact = Contact.objects.filter(
            organization=organization, email=email
        ).first()

        if contact is None:
            return Contact.objects.create(
                organization=organization, source='form',
                custom_fields=custom,
                **{k: v for k, v in standard.items() if k != 'email'},
                email=email,
            )

        updated = []
        for key, value in standard.items():
            if key == 'email':
                continue
            setattr(contact, key, value)
            updated.append(key)
        if custom:
            contact.custom_fields = CustomFieldService.merge(
                organization, contact.custom_fields, custom,
            )
            updated.append('custom_fields')
        if updated:
            contact.save(update_fields=updated + ['updated_at'])
        return contact


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
