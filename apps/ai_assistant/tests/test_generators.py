"""
Tests for the form, email template and campaign generators.

All driven by stubbed payloads: these check what the code builds from a model's
output, which is the part that has to be right regardless of which model or
provider produced it.
"""
import json

from django.test import SimpleTestCase, TestCase

from apps.accounts.models import Organization, User
from apps.ai_assistant.generators import campaigns, email_templates, forms
from apps.ai_assistant.models import GenerationJob
from apps.ai_assistant.unlayer import SCHEMA_VERSION, build_design, build_html
from apps.campaigns.models import Campaign
from apps.forms.models import Form, FormField
from apps.templates.models import EmailTemplate


class JobFixtureMixin:
    def setUp(self):
        self.org = Organization.objects.create(name='Gen Org', slug='gen-org')
        self.user = User.objects.create_user(
            email='gen@example.com', password='x', organization=self.org,
        )

    def _job(self, kind, prompt='A guide download for small agencies'):
        return GenerationJob.objects.create(
            organization=self.org, created_by=self.user, kind=kind, prompt=prompt,
        )


class FormGeneratorTests(JobFixtureMixin, TestCase):
    def _payload(self, fields):
        return {
            'name': 'Guide Download',
            'description': 'Get the guide.',
            'submit_button_text': 'Send it',
            'success_message': 'Check your inbox.',
            'fields': fields,
        }

    def _field(self, **kwargs):
        base = {
            'label': 'Email', 'field_type': 'email', 'is_required': True,
            'placeholder': '', 'help_text': '', 'options': [],
            'contact_field_mapping': 'email',
        }
        return {**base, **kwargs}

    def test_builds_a_form_with_its_fields(self):
        job = self._job(GenerationJob.KIND_FORM)
        form = forms.create(job, self._payload([
            self._field(),
            self._field(label='First name', field_type='text',
                        contact_field_mapping='first_name', is_required=False),
        ]))

        self.assertEqual(form.name, 'Guide Download')
        self.assertEqual(form.submit_button_text, 'Send it')
        # Not public until reviewed.
        self.assertEqual(form.status, 'inactive')
        self.assertEqual(form.fields.count(), 2)
        self.assertEqual(
            list(form.fields.order_by('order').values_list('label', flat=True)),
            ['Email', 'First name'],
        )

    def test_invalid_field_type_is_dropped_not_saved(self):
        job = self._job(GenerationJob.KIND_FORM)
        form = forms.create(job, self._payload([
            self._field(),
            self._field(label='Mood', field_type='slider',
                        contact_field_mapping=''),
        ]))

        labels = list(form.fields.values_list('label', flat=True))
        self.assertIn('Email', labels)
        self.assertNotIn('Mood', labels)

    def test_invalid_contact_mapping_is_cleared_not_saved(self):
        job = self._job(GenerationJob.KIND_FORM)
        form = forms.create(job, self._payload([
            self._field(),
            self._field(label='Budget', field_type='text',
                        contact_field_mapping='annual_revenue'),
        ]))

        budget = form.fields.get(label='Budget')
        self.assertEqual(budget.contact_field_mapping, '')

    def test_a_form_with_no_email_field_gets_one(self):
        """Without a mapped email the form collects replies that never become leads."""
        job = self._job(GenerationJob.KIND_FORM)
        form = forms.create(job, self._payload([
            self._field(label='Company', field_type='text',
                        contact_field_mapping='company'),
        ]))

        email_field = form.fields.get(contact_field_mapping='email')
        self.assertEqual(email_field.field_type, 'email')
        self.assertTrue(email_field.is_required)
        self.assertEqual(email_field.order, 0)

    def test_an_unmapped_email_field_is_mapped(self):
        job = self._job(GenerationJob.KIND_FORM)
        form = forms.create(job, self._payload([
            self._field(contact_field_mapping=''),
        ]))

        self.assertEqual(form.fields.count(), 1)
        self.assertEqual(form.fields.first().contact_field_mapping, 'email')

    def test_choice_field_without_options_is_dropped(self):
        job = self._job(GenerationJob.KIND_FORM)
        form = forms.create(job, self._payload([
            self._field(),
            self._field(label='Country', field_type='dropdown',
                        contact_field_mapping='', options=[]),
        ]))
        self.assertNotIn('Country', list(form.fields.values_list('label', flat=True)))

    def test_choice_field_keeps_its_options(self):
        job = self._job(GenerationJob.KIND_FORM)
        form = forms.create(job, self._payload([
            self._field(),
            self._field(label='Country', field_type='dropdown',
                        contact_field_mapping='', options=['UK', 'US']),
        ]))
        self.assertEqual(form.fields.get(label='Country').options, ['UK', 'US'])

    def test_presentational_fields_are_never_required_or_mapped(self):
        job = self._job(GenerationJob.KIND_FORM)
        form = forms.create(job, self._payload([
            self._field(),
            self._field(label='About you', field_type='section',
                        is_required=True, contact_field_mapping='company'),
        ]))
        section = form.fields.get(label='About you')
        self.assertFalse(section.is_required)
        self.assertEqual(section.contact_field_mapping, '')


class UnlayerBuilderTests(SimpleTestCase):
    """
    The editor loads design_json and nothing else, so a wrong shape here means
    a template that opens blank and is destroyed by the first save.
    """

    BLOCKS = [
        {'type': 'heading', 'text': 'Stop guessing', 'href': '', 'level': 1},
        {'type': 'paragraph', 'text': 'Some body copy.', 'href': '', 'level': 2},
        {'type': 'button', 'text': 'Read it', 'href': 'https://example.test', 'level': 2},
    ]

    def test_design_has_the_expected_envelope(self):
        design, kept = build_design(self.BLOCKS, preheader='A preview line')

        self.assertEqual(kept, 3)
        self.assertEqual(design['schemaVersion'], SCHEMA_VERSION)
        self.assertEqual(sorted(design.keys()), ['body', 'counters', 'schemaVersion'])
        self.assertEqual(
            sorted(design['body'].keys()),
            ['footers', 'headers', 'id', 'rows', 'values'],
        )
        self.assertEqual(design['body']['values']['preheaderText'], 'A preview line')

    def test_one_row_per_block_each_with_one_column(self):
        design, _ = build_design(self.BLOCKS)
        rows = design['body']['rows']

        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row['cells'], [1])
            self.assertEqual(len(row['columns']), 1)
            self.assertEqual(len(row['columns'][0]['contents']), 1)

    def test_counters_match_the_block_html_ids(self):
        """Unlayer keys its ids off the counters; a mismatch breaks the design."""
        design, _ = build_design(self.BLOCKS)
        counters = design['counters']

        self.assertEqual(counters['u_row'], 3)
        self.assertEqual(counters['u_column'], 3)
        self.assertEqual(counters['u_content_heading'], 1)
        self.assertEqual(counters['u_content_paragraph'], 1)
        self.assertEqual(counters['u_content_button'], 1)

        ids = [
            r['columns'][0]['contents'][0]['values']['_meta']['htmlID']
            for r in design['body']['rows']
        ]
        self.assertEqual(
            ids,
            ['u_content_heading_1', 'u_content_paragraph_1', 'u_content_button_1'],
        )

    def test_text_is_stored_as_a_lexical_document(self):
        """Unlayer does not store HTML here — it stores Lexical JSON."""
        design, _ = build_design(self.BLOCKS)
        heading = design['body']['rows'][0]['columns'][0]['contents'][0]

        doc = json.loads(heading['values']['textJson'])
        paragraph = doc['root']['children'][0]
        self.assertEqual(paragraph['type'], 'heading-paragraph')
        self.assertEqual(paragraph['children'][0]['text'], 'Stop guessing')
        self.assertEqual(paragraph['children'][0]['type'], 'extended-text')

    def test_button_carries_its_link_and_inline_flag(self):
        design, _ = build_design(self.BLOCKS)
        button = design['body']['rows'][2]['columns'][0]['contents'][0]

        self.assertEqual(button['type'], 'button')
        self.assertEqual(
            button['values']['href']['values']['href'], 'https://example.test',
        )
        doc = json.loads(button['values']['textJson'])
        self.assertTrue(doc['root']['children'][0]['isInlineTool'])

    def test_every_block_carries_the_editor_control_keys(self):
        design, _ = build_design(self.BLOCKS)
        for row in design['body']['rows']:
            values = row['columns'][0]['contents'][0]['values']
            for key in ('selectable', 'draggable', 'duplicatable',
                        'deletable', 'hideable', 'locked', '_meta'):
                self.assertIn(key, values)

    def test_unsupported_and_empty_blocks_are_skipped(self):
        design, kept = build_design([
            {'type': 'heading', 'text': 'Kept', 'href': '', 'level': 1},
            {'type': 'image', 'text': 'Dropped', 'href': '', 'level': 2},
            {'type': 'paragraph', 'text': '   ', 'href': '', 'level': 2},
        ])
        self.assertEqual(kept, 1)
        self.assertEqual(len(design['body']['rows']), 1)

    def test_html_fallback_escapes_and_includes_every_block(self):
        html = build_html(self.BLOCKS + [
            {'type': 'paragraph', 'text': '<script>x</script>', 'href': '', 'level': 2},
        ])
        self.assertIn('Stop guessing', html)
        self.assertIn('https://example.test', html)
        self.assertNotIn('<script>', html)


class EmailTemplateGeneratorTests(JobFixtureMixin, TestCase):
    PAYLOAD = {
        'name': 'Bounce rate webinar',
        'subject': 'Stop landing in spam',
        'preheader': 'A 45 minute session on deliverability.',
        'blocks': UnlayerBuilderTests.BLOCKS,
    }

    def test_creates_a_template_the_editor_can_load(self):
        job = self._job(GenerationJob.KIND_EMAIL_TEMPLATE)
        template = email_templates.create(job, self.PAYLOAD)

        self.assertEqual(template.subject, 'Stop landing in spam')
        self.assertEqual(template.design_json['schemaVersion'], SCHEMA_VERSION)
        self.assertEqual(len(template.design_json['body']['rows']), 3)
        # Both halves are stored: the design is what the editor loads, the HTML
        # is what sends if nobody ever opens it.
        self.assertIn('Stop guessing', template.html_content)

    def test_rejects_a_payload_with_no_usable_blocks(self):
        self.assertIsNotNone(email_templates.validate({'blocks': []}))
        self.assertIsNotNone(email_templates.validate(
            {'blocks': [{'type': 'image', 'text': 'x'}]}
        ))
        self.assertIsNone(email_templates.validate(self.PAYLOAD))


class CampaignGeneratorTests(JobFixtureMixin, TestCase):
    def test_creates_a_draft_campaign_with_its_template_attached(self):
        job = self._job(GenerationJob.KIND_CAMPAIGN)
        campaign = campaigns.create(job, {
            **EmailTemplateGeneratorTests.PAYLOAD,
            'name': 'Q3 webinar invite',
        })

        self.assertEqual(campaign.status, 'draft')
        self.assertEqual(campaign.name, 'Q3 webinar invite')
        self.assertEqual(campaign.subject, 'Stop landing in spam')
        self.assertEqual(
            campaign.preheader_text, 'A 45 minute session on deliverability.',
        )
        self.assertIsNotNone(campaign.template)
        self.assertEqual(campaign.template.design_json['schemaVersion'], SCHEMA_VERSION)

    def test_recipients_are_left_for_the_user(self):
        """Audience is a decision with consequences; generation does not make it."""
        job = self._job(GenerationJob.KIND_CAMPAIGN)
        campaign = campaigns.create(job, {
            **EmailTemplateGeneratorTests.PAYLOAD, 'name': 'Q3 invite',
        })
        self.assertEqual(campaign.recipient_count, 0)
        self.assertIsNone(campaign.scheduled_at)
