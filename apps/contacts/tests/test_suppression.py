"""
Who may not be sent marketing email.

There were three answers to this and they disagreed: campaigns excluded the
unsubscribed and the bounced, sequences excluded only the unsubscribed, and
workflows excluded nobody — so a workflow would mail someone who had opted
out, and a sequence would keep mailing an address that does not exist.

`Contact.email_suppressed` is the one answer and `Contact.objects.mailable()`
is its queryset form. The pair must agree, which is the point of the first
class here.
"""
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization, User
from apps.contacts.models import Contact


class SuppressionTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )

    def _contact(self, email='ada@example.com', **kwargs):
        return Contact.objects.create(
            organization=self.org, email=email, **kwargs
        )


class DefinitionTests(SuppressionTestCase):
    def test_an_ordinary_contact_may_be_emailed(self):
        self.assertIsNone(self._contact().email_suppressed)

    def test_an_unsubscribed_contact_may_not(self):
        contact = self._contact()
        contact.unsubscribe()
        self.assertEqual(contact.email_suppressed, 'unsubscribed')

    def test_a_bounced_contact_may_not(self):
        contact = self._contact()
        contact.mark_bounced('hard')
        self.assertIn('bounce', contact.email_suppressed)

    def test_a_soft_bounce_is_suppressed_too(self):
        """Matches what campaigns already did; relaxing it would widen reach."""
        contact = self._contact()
        contact.mark_bounced('soft')
        self.assertIsNotNone(contact.email_suppressed)

    def test_a_complaint_may_not(self):
        contact = self._contact()
        contact.mark_complained()
        # mark_complained also clears is_subscribed, so either reason is
        # correct — what matters is that it is suppressed.
        self.assertIsNotNone(contact.email_suppressed)

    def test_the_reason_names_the_rule(self):
        contact = self._contact()
        contact.complained_at = timezone.now()
        contact.save(update_fields=['complained_at'])
        self.assertIn('spam', contact.email_suppressed)


class QuerysetAgreementTests(SuppressionTestCase):
    """
    The property and the queryset must pick the same people.

    They are two implementations of one rule, which is how the three
    definitions this replaced drifted in the first place.
    """

    def test_they_agree_across_every_state(self):
        ok = self._contact('ok@example.com')

        gone = self._contact('gone@example.com')
        gone.unsubscribe()

        bounced = self._contact('bounced@example.com')
        bounced.mark_bounced('hard')

        soft = self._contact('soft@example.com')
        soft.mark_bounced('soft')

        angry = self._contact('angry@example.com')
        angry.mark_complained()

        by_queryset = set(
            Contact.objects.mailable()
            .filter(organization=self.org)
            .values_list('id', flat=True)
        )
        by_property = {
            contact.id
            for contact in Contact.objects.filter(organization=self.org)
            if contact.email_suppressed is None
        }

        self.assertEqual(by_queryset, by_property)
        self.assertEqual(by_queryset, {ok.id})


class WorkflowSendTests(SuppressionTestCase):
    """The path that checked nothing at all."""

    def setUp(self):
        super().setUp()
        from apps.templates.models import EmailTemplate
        from apps.workflows.models import Workflow, WorkflowExecution, WorkflowNode

        self.template = EmailTemplate.objects.create(
            organization=self.org, name='Welcome', subject='Hi',
            html_content='<p>Hi</p>',
        )
        self.contact = self._contact()
        self.workflow = Workflow.objects.create(
            organization=self.org, name='Flow', status='active',
        )
        self.node = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.ACTION_SEND_EMAIL,
            config={'template_id': str(self.template.id)},
        )
        self.execution = WorkflowExecution.objects.create(
            workflow=self.workflow, contact=self.contact, status='active',
        )

    def _send(self):
        from apps.workflows.services import WorkflowExecutionService

        return WorkflowExecutionService._handle_node(self.execution, self.node)

    def test_a_subscribed_contact_is_emailed(self):
        from django.core import mail

        with patch('apps.email_config.services.EmailConfigService.resolve') as resolve:
            resolve.return_value.unavailable = ''
            resolve.return_value.connection = mail.get_connection(
                'django.core.mail.backends.locmem.EmailBackend'
            )
            resolve.return_value.sender.return_value = ('Acme <a@acme.test>', None)
            result = self._send()

        self.assertTrue(result['output'].get('email_sent'))
        self.assertEqual(len(mail.outbox), 1)

    def test_an_unsubscribed_contact_is_not_emailed(self):
        """The bug: this used to send."""
        from django.core import mail

        self.contact.unsubscribe()

        result = self._send()

        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(result['output']['email_sent'])
        self.assertEqual(result['output']['skipped'], 'unsubscribed')

    def test_a_bounced_contact_is_not_emailed(self):
        from django.core import mail

        self.contact.mark_bounced('hard')

        self._send()
        self.assertEqual(len(mail.outbox), 0)

    def test_skipping_does_not_fail_the_execution(self):
        """
        Opting out is normal, not an error. Raising here would fail the step,
        retry it three times and notify an admin — and would stop any
        non-email steps after it from running.
        """
        self.contact.unsubscribe()

        result = self._send()

        self.assertNotIn('error', result)
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, 'active')

    def test_notifying_the_team_is_not_suppressed(self):
        """
        Internal mail goes to a colleague, not to the contact, so the
        contact's own preferences have nothing to do with it.
        """
        from apps.core.mail import MailResult
        from apps.workflows.models import WorkflowNode

        self.contact.unsubscribe()
        notify = WorkflowNode.objects.create(
            workflow=self.workflow, node_type=WorkflowNode.ACTION_NOTIFY_TEAM,
            config={'user_id': str(self.user.id), 'subject': 'Heads up'},
        )

        from apps.workflows.services import WorkflowExecutionService

        with patch(
            'apps.core.mail.send_transactional_email',
            return_value=MailResult(True, ''),
        ) as send:
            WorkflowExecutionService._handle_node(self.execution, notify)

        send.assert_called_once()


class SequenceSendTests(SuppressionTestCase):
    """Sequences checked the subscription but not the bounce."""

    def _step(self, sequence):
        """A sequence with no steps refuses every enrollment."""
        from apps.sequences.models import SequenceStep
        from apps.templates.models import EmailTemplate

        template = EmailTemplate.objects.create(
            organization=self.org, name='Step one', subject='Hi',
            html_content='<p>Hi</p>',
        )
        return SequenceStep.objects.create(
            sequence=sequence, position=0, subject='Hi', template=template,
        )

    def test_a_bounced_contact_stops_the_sequence(self):
        from apps.sequences.models import EmailSequence, SequenceEnrollment

        sequence = EmailSequence.objects.create(
            organization=self.org, name='Onboarding', status='active',
        )
        self._step(sequence)
        contact = self._contact()
        contact.mark_bounced('hard')
        enrollment = SequenceEnrollment.objects.create(
            sequence=sequence, contact=contact, status='active',
        )

        from apps.sequences.services import SequenceEnrollmentService

        SequenceEnrollmentService._process_enrollment(enrollment)

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, 'unsubscribed')

    def test_a_bounced_contact_cannot_be_bulk_enrolled(self):
        from apps.sequences.models import EmailSequence, SequenceEnrollment
        from apps.sequences.services import SequenceEnrollmentService

        sequence = EmailSequence.objects.create(
            organization=self.org, name='Onboarding', status='active',
        )
        self._step(sequence)
        ok = self._contact('ok@example.com')
        bounced = self._contact('bounced@example.com')
        bounced.mark_bounced('hard')

        SequenceEnrollmentService.enroll_contacts_bulk(
            sequence, [str(ok.id), str(bounced.id)],
        )

        enrolled = set(
            SequenceEnrollment.objects.filter(sequence=sequence)
            .values_list('contact_id', flat=True)
        )
        self.assertEqual(enrolled, {ok.id})


class CampaignRecipientTests(SuppressionTestCase):
    def test_the_shared_filter_does_not_widen_who_gets_a_campaign(self):
        """
        Campaigns already excluded the unsubscribed and the bounced. Moving
        them onto the shared filter must not let anyone new in.
        """
        from apps.campaigns.models import Campaign
        from apps.campaigns.services import CampaignService

        ok = self._contact('ok@example.com')
        gone = self._contact('gone@example.com')
        gone.unsubscribe()
        bounced = self._contact('bounced@example.com')
        bounced.mark_bounced('hard')

        campaign = Campaign.objects.create(
            organization=self.org, name='Newsletter', subject='Hi',
            recipient_type='all',
        )

        recipients = set(
            CampaignService.calculate_recipients(campaign)
            .values_list('id', flat=True)
        )
        self.assertEqual(recipients, {ok.id})
