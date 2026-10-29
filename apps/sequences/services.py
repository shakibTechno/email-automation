"""
Services for the Email Sequences app.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class SequenceService:
    @staticmethod
    def create_sequence(organization, data, created_by=None):
        from .models import EmailSequence
        return EmailSequence.objects.create(
            organization=organization,
            created_by=created_by,
            name=data['name'],
            description=data.get('description', ''),
            sender_name=data.get('sender_name', ''),
            sender_email=data.get('sender_email', ''),
            reply_to_email=data.get('reply_to_email', ''),
            allow_reenrollment=data.get('allow_reenrollment', False),
        )

    @staticmethod
    def duplicate_sequence(sequence, created_by=None):
        from .models import SequenceStep
        with transaction.atomic():
            new_seq = EmailSequence.objects.create(
                organization=sequence.organization,
                created_by=created_by,
                name=f"Copy of {sequence.name}",
                description=sequence.description,
                sender_name=sequence.sender_name,
                sender_email=sequence.sender_email,
                reply_to_email=sequence.reply_to_email,
                allow_reenrollment=sequence.allow_reenrollment,
                status='draft',
            )
            for step in sequence.steps.all():
                SequenceStep.objects.create(
                    sequence=new_seq,
                    position=step.position,
                    subject=step.subject,
                    template=step.template,
                    delay_days=step.delay_days,
                    delay_hours=step.delay_hours,
                )
            return new_seq

    @staticmethod
    def reorder_steps(sequence, step_ids):
        """Accept an ordered list of step UUIDs; update positions accordingly."""
        from .models import SequenceStep
        for pos, step_id in enumerate(step_ids):
            SequenceStep.objects.filter(id=step_id, sequence=sequence).update(position=pos)


class SequenceEnrollmentService:
    @staticmethod
    def enroll_contact(sequence, contact, enrolled_by=None):
        """
        Enroll a contact in a sequence. Returns (enrollment, created).
        Raises ValueError if sequence is not active or contact is already enrolled.
        """
        from .models import SequenceEnrollment, SequenceStepExecution

        if sequence.status != 'active':
            raise ValueError("Sequence must be active to enroll contacts.")

        first_step = sequence.steps.order_by('position').first()
        if not first_step:
            raise ValueError("Sequence has no steps.")

        # Check existing enrollment
        existing = SequenceEnrollment.objects.filter(sequence=sequence, contact=contact).first()
        if existing:
            if existing.status in ('active', 'paused'):
                raise ValueError("Contact is already enrolled in this sequence.")
            if existing.status in ('completed', 'unsubscribed', 'cancelled') and not sequence.allow_reenrollment:
                raise ValueError("Contact has already gone through this sequence and re-enrollment is disabled.")
            # Re-enroll: reset
            existing.status = 'active'
            existing.current_step_position = 0
            existing.completed_at = None
            now = timezone.now()
            # Schedule first step
            delay = timedelta(hours=first_step.total_delay_hours)
            existing.next_send_at = now + delay if delay.total_seconds() > 0 else now
            existing.save()
            # Clear old step executions
            existing.step_executions.all().delete()
            return existing, False

        now = timezone.now()
        delay = timedelta(hours=first_step.total_delay_hours)
        next_send = now + delay if delay.total_seconds() > 0 else now

        enrollment = SequenceEnrollment.objects.create(
            sequence=sequence,
            contact=contact,
            enrolled_by=enrolled_by,
            current_step_position=0,
            next_send_at=next_send,
        )
        return enrollment, True

    @staticmethod
    def enroll_contacts_bulk(sequence, contact_ids, enrolled_by=None):
        from apps.contacts.models import Contact
        contacts = Contact.objects.filter(
            id__in=contact_ids,
            organization=sequence.organization,
            is_subscribed=True,
        )
        enrolled = 0
        errors = []
        for contact in contacts:
            try:
                SequenceEnrollmentService.enroll_contact(sequence, contact, enrolled_by=enrolled_by)
                enrolled += 1
            except ValueError as e:
                errors.append({'contact': str(contact.id), 'error': str(e)})
        return {'enrolled': enrolled, 'errors': errors}

    @staticmethod
    def cancel_enrollment(enrollment):
        enrollment.status = 'cancelled'
        enrollment.save(update_fields=['status'])

    @staticmethod
    def process_due_enrollments():
        """Process all enrollments where next_send_at has passed. Called by Celery Beat."""
        from .models import SequenceEnrollment
        now = timezone.now()
        due = SequenceEnrollment.objects.filter(
            status='active',
            next_send_at__lte=now,
            sequence__status='active',
        ).select_related('sequence', 'contact', 'enrolled_by')

        processed = 0
        for enrollment in due:
            try:
                SequenceEnrollmentService._process_enrollment(enrollment)
                processed += 1
            except Exception as exc:
                logger.exception(f"Error processing enrollment {enrollment.id}: {exc}")
        return processed

    @staticmethod
    def _process_enrollment(enrollment):
        from .models import SequenceStep, SequenceStepExecution
        from apps.campaigns.services import CampaignService

        step = enrollment.sequence.steps.filter(position=enrollment.current_step_position).first()
        if not step:
            enrollment.status = 'completed'
            enrollment.completed_at = timezone.now()
            enrollment.next_send_at = None
            enrollment.save(update_fields=['status', 'completed_at', 'next_send_at'])
            return

        contact = enrollment.contact
        if not contact.is_subscribed:
            enrollment.status = 'unsubscribed'
            enrollment.save(update_fields=['status'])
            return

        # Send the email
        postal_status = None
        try:
            postal_status = SequenceEnrollmentService._send_step_email(enrollment, step)
            step_exec_status = 'sent'
            error_msg = ''
        except Exception as exc:
            logger.exception(f"Failed to send sequence step email: {exc}")
            step_exec_status = 'failed'
            error_msg = str(exc)

        now = timezone.now()
        defaults = {
            'status': step_exec_status,
            'scheduled_at': enrollment.next_send_at or now,
            'sent_at': now if step_exec_status == 'sent' else None,
            'error_message': error_msg,
        }
        # Provider ids, so a later delivery or bounce webhook can find this row.
        if postal_status:
            defaults['postal_id'] = postal_status.get('postal_id')
            defaults['postal_token'] = postal_status.get('token') or ''

        SequenceStepExecution.objects.update_or_create(
            enrollment=enrollment,
            step=step,
            defaults=defaults,
        )

        # Advance to next step
        next_step = enrollment.sequence.steps.filter(position__gt=enrollment.current_step_position).order_by('position').first()
        if next_step:
            enrollment.current_step_position = next_step.position
            delay = timedelta(hours=next_step.total_delay_hours)
            enrollment.next_send_at = now + delay if delay.total_seconds() > 0 else now
            enrollment.save(update_fields=['current_step_position', 'next_send_at'])
        else:
            enrollment.status = 'completed'
            enrollment.completed_at = now
            enrollment.next_send_at = None
            enrollment.save(update_fields=['status', 'completed_at', 'next_send_at', 'current_step_position'])

    @staticmethod
    def _send_step_email(enrollment, step):
        from django.core.mail import EmailMultiAlternatives
        from apps.email_config.services import EmailConfigService

        sequence = enrollment.sequence
        contact = enrollment.contact
        template = step.template

        if not template:
            raise ValueError(f"Step {step.position} has no template assigned.")

        html_content = template.html_content or ''
        merge_data = {
            'first_name': contact.first_name or '',
            'last_name': contact.last_name or '',
            'email': contact.email,
            'company': contact.company or '',
        }
        for key, value in merge_data.items():
            html_content = html_content.replace(f'{{{{{key}}}}}', str(value))

        # Sequence sender overrides org defaults, but only where the resolved
        # backend will accept the address.
        identity = EmailConfigService.resolve(sequence.organization)
        if identity.unavailable:
            raise RuntimeError(identity.unavailable)
        from_email, reply_to = identity.sender(
            name=sequence.sender_name,
            email=sequence.sender_email,
            reply_to=sequence.reply_to_email,
        )
        connection = identity.connection
        msg = EmailMultiAlternatives(
            subject=step.subject,
            body='',
            from_email=from_email,
            to=[contact.email],
            reply_to=reply_to,
            connection=connection,
            headers={'X-Sequence-ID': str(sequence.id)},
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send()
        # Returned so the caller can store the provider ids on the execution.
        return getattr(msg, 'postal_status', None)
