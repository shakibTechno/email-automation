"""
Tests for the form, email template and campaign generators.

All driven by stubbed payloads: these check what the code builds from a model's
output, which is the part that has to be right regardless of which model or
provider produced it.
"""
import json

from django.test import SimpleTestCase, TestCase

from apps.accounts.models import Organization, User
from apps.ai_assistant.generators import email_templates, forms
from apps.forms.models import (
    default_branding, default_layout, default_styling,
)
from apps.ai_assistant.models import GenerationJob
from apps.ai_assistant.unlayer import SCHEMA_VERSION
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


class EmailTemplateGeneratorTests(JobFixtureMixin, TestCase):
    """
    Typed blocks stay editable in the drag-and-drop editor; an html block buys
    a layout the typed blocks cannot express, and costs code-only editing. The
    mix is the point — neither the three-block vocabulary nor one HTML blob.
    """

    HERO = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0"><tr><td bgcolor="#1a1a2e" align="center" style="padding:32px">'
        '<h1 style="color:#ffffff;font-size:28px;margin:0">Stop guessing</h1>'
        '</td></tr></table>'
    )

    BLOCKS = [
        {'type': 'html', 'text': '', 'html': HERO, 'href': '', 'level': 2},
        {'type': 'heading', 'text': 'Your bounce rate is a number',
         'html': '', 'href': '', 'level': 2},
        {'type': 'paragraph', 'text': 'It is telling you something specific.',
         'html': '', 'href': '', 'level': 2},
        {'type': 'button', 'text': 'Save my seat', 'html': '',
         'href': 'https://example.com/webinar', 'level': 2},
    ]

    PAYLOAD = {
        'name': 'Bounce rate webinar',
        'subject': 'Stop landing in spam',
        'preheader': 'A 45 minute session on deliverability.',
        'blocks': BLOCKS,
    }

    def _template(self, **overrides):
        job = self._job(GenerationJob.KIND_EMAIL_TEMPLATE)
        return email_templates.create(job, {**self.PAYLOAD, **overrides})

    def _contents(self, template):
        return [
            row['columns'][0]['contents'][0]
            for row in template.design_json['body']['rows']
        ]

    def test_typed_blocks_stay_editable_and_html_blocks_are_html(self):
        template = self._template()

        self.assertEqual(template.design_json['schemaVersion'], SCHEMA_VERSION)
        self.assertEqual(
            [c['type'] for c in self._contents(template)],
            ['html', 'heading', 'paragraph', 'button'],
            'each block keeps its own Unlayer tool',
        )

    def test_the_html_block_carries_its_markup(self):
        template = self._template()
        html_block = self._contents(template)[0]
        self.assertIn('bgcolor="#1a1a2e"', html_block['values']['html'])

    def test_table_layout_and_inline_styles_survive(self):
        """
        Email layout is tables and presentational attributes. A sanitizer tuned
        for landing pages would strip exactly what makes the email render.
        """
        template = self._template()
        for fragment in ('cellpadding="0"', 'bgcolor="#1a1a2e"', 'align="center"'):
            self.assertIn(fragment, template.html_content, fragment)

    def test_script_in_an_html_block_is_removed(self):
        template = self._template(blocks=[
            {'type': 'html', 'text': '',
             'html': self.HERO + '<script>fetch("https://evil.test")</script>',
             'href': '', 'level': 2},
            *self.BLOCKS[1:],
        ])

        self.assertNotIn('<script', template.html_content)
        self.assertNotIn('evil.test', template.html_content)
        self.assertIn('Stop guessing', template.html_content)

    def test_the_fallback_html_renders_both_kinds(self):
        """
        Unlayer regenerates html_content on first save, so this only matters
        for a template nobody opens — but that one still has to send.
        """
        template = self._template()

        self.assertIn('Stop guessing', template.html_content)       # html block
        self.assertIn('Your bounce rate', template.html_content)    # typed block
        self.assertIn('https://example.com/webinar', template.html_content)

    def test_words_in_a_typed_block_are_escaped_but_markup_is_not(self):
        """A typed block is plain text: angle brackets in it are words."""
        template = self._template(blocks=[
            {'type': 'paragraph', 'text': 'Costs <10 minutes & no setup',
             'html': '', 'href': '', 'level': 2},
            {'type': 'html', 'text': '', 'html': self.HERO, 'href': '', 'level': 2},
        ])

        self.assertIn('&lt;10 minutes', template.html_content)
        self.assertIn('<table', template.html_content)

    def test_the_preheader_reaches_the_design(self):
        template = self._template()
        self.assertEqual(
            template.design_json['body']['values']['preheaderText'],
            'A 45 minute session on deliverability.',
        )

    def test_unusable_blocks_are_skipped_not_guessed_at(self):
        template = self._template(blocks=[
            *self.BLOCKS,
            {'type': 'carousel', 'text': 'x', 'html': '', 'href': '', 'level': 2},
            {'type': 'html', 'text': '', 'html': '   ', 'href': '', 'level': 2},
            {'type': 'paragraph', 'text': '', 'html': '', 'href': '', 'level': 2},
        ])
        self.assertEqual(len(self._contents(template)), 4)

    def test_rejects_output_that_is_not_an_email(self):
        self.assertIsNotNone(email_templates.validate({'blocks': []}))
        self.assertIsNotNone(email_templates.validate(
            {'blocks': [{'type': 'image', 'text': 'x'}]}
        ))
        self.assertIsNotNone(
            email_templates.validate({'blocks': [
                {'type': 'html', 'html': '<div><span></span></div>'},
            ]}),
            'markup with no readable words is not an email',
        )
        self.assertIsNone(email_templates.validate(self.PAYLOAD))


class GeneratableKindsTests(TestCase):
    """
    Campaign generation was withdrawn: picking an audience, a schedule and a
    sender is the part that carries the risk, and a drafted campaign invited
    sending without deciding any of it.
    """

    def test_campaign_is_not_generatable(self):
        self.assertNotIn(
            GenerationJob.KIND_CAMPAIGN, GenerationJob.GENERATABLE_KINDS
        )

    def test_the_kind_is_still_readable_on_jobs_already_recorded(self):
        """Old rows and their FK must still load."""
        self.assertIn(
            GenerationJob.KIND_CAMPAIGN,
            {kind for kind, _ in GenerationJob.KIND_CHOICES},
        )

    def test_nothing_claims_to_generate_a_campaign(self):
        from apps.ai_assistant.services import AIError, _generator_for

        with self.assertRaises(AIError):
            _generator_for(GenerationJob.KIND_CAMPAIGN)


class FormDesignGeneratorTests(JobFixtureMixin, TestCase):
    """
    The builder has three steps and generation used to fill only the first, so
    every generated form arrived as a default-grey stack. The model supplies
    design intent; the concrete values are derived.
    """

    PAYLOAD = {
        'name': 'Deliverability guide',
        'description': 'Get the guide.',
        'submit_button_text': 'Send it to me',
        'success_message': 'Check your inbox.',
        'header_text': 'Stop landing in spam',
        'footer_text': 'One email a month. Unsubscribe any time.',
        'primary_color': '#c2410c',
        'style': 'rounded',
        'columns': 2,
        'show_gdpr_consent': True,
        'gdpr_consent_text': 'Acme may email you about deliverability.',
        'fields': [
            {'label': 'First name', 'field_type': 'text', 'is_required': False,
             'placeholder': 'Ada', 'help_text': '', 'options': [],
             'contact_field_mapping': 'first_name', 'width': 'half'},
            {'label': 'Last name', 'field_type': 'text', 'is_required': False,
             'placeholder': 'Lovelace', 'help_text': '', 'options': [],
             'contact_field_mapping': 'last_name', 'width': 'half'},
            {'label': 'Work email', 'field_type': 'email', 'is_required': True,
             'placeholder': 'you@company.com', 'help_text': '', 'options': [],
             'contact_field_mapping': 'email', 'width': 'full'},
        ],
    }

    def _form(self, **overrides):
        job = self._job(GenerationJob.KIND_FORM)
        return forms.create(job, {**self.PAYLOAD, **overrides})

    def test_the_brand_colour_reaches_every_place_it_belongs(self):
        form = self._form()

        self.assertEqual(form.styling['primaryColor'], '#c2410c')
        self.assertEqual(form.styling['buttonStyle']['backgroundColor'], '#c2410c')
        self.assertEqual(form.styling['inputStyle']['focusBorderColor'], '#c2410c')
        self.assertEqual(form.styling['inputStyle']['focusRingColor'], '#c2410c33')
        # A hover identical to the resting colour reads as a dead control.
        self.assertNotEqual(
            form.styling['buttonStyle']['hoverBackgroundColor'], '#c2410c'
        )

    def test_the_style_choice_changes_the_shape(self):
        rounded = self._form(style='rounded')
        classic = self._form(style='classic')

        self.assertEqual(rounded.styling['borderRadius'], '12px')
        self.assertEqual(classic.styling['borderRadius'], '2px')
        self.assertTrue(rounded.styling['buttonStyle']['fullWidth'])
        self.assertFalse(classic.styling['buttonStyle']['fullWidth'])

    def test_branding_and_layout_are_filled(self):
        form = self._form()

        self.assertEqual(form.branding['headerText'], 'Stop landing in spam')
        self.assertIn('Unsubscribe', form.branding['footerText'])
        self.assertEqual(form.layout['columns'], 2)
        # Two columns need room, or the pair wraps anyway.
        self.assertEqual(form.layout['maxWidth'], '640px')

    def test_field_widths_are_stored(self):
        form = self._form()
        widths = list(
            form.fields.order_by('order').values_list('label', 'width')
        )
        self.assertEqual(
            widths,
            [('First name', 'half'), ('Last name', 'half'), ('Work email', 'full')],
        )

    def test_no_key_the_design_panel_reads_is_missing(self):
        """
        The panel reads these blobs directly; a missing key renders as an empty
        input rather than falling back to anything.
        """
        form = self._form()

        for key in default_styling():
            self.assertIn(key, form.styling, key)
        for key in default_styling()['buttonStyle']:
            self.assertIn(key, form.styling['buttonStyle'], key)
        for key in default_branding():
            self.assertIn(key, form.branding, key)
        for key in default_layout():
            self.assertIn(key, form.layout, key)

    def test_a_colour_the_model_invented_falls_back(self):
        form = self._form(primary_color='burnt orange')
        self.assertEqual(form.styling['primaryColor'], '#3b82f6')

    def test_a_short_hex_is_expanded(self):
        form = self._form(primary_color='#0A5')
        self.assertEqual(form.styling['primaryColor'], '#00aa55')

    def test_an_unknown_style_falls_back_rather_than_failing(self):
        form = self._form(style='brutalist')
        self.assertEqual(
            form.styling['borderRadius'], forms.STYLE_PRESETS['minimal']['borderRadius']
        )

    def test_consent_is_stored_with_its_wording(self):
        form = self._form()
        self.assertTrue(form.show_gdpr_consent)
        self.assertIn('Acme may email you', form.gdpr_consent_text)

    def test_consent_without_wording_is_turned_off(self):
        """An unlabelled checkbox asks for agreement to nothing."""
        form = self._form(show_gdpr_consent=True, gdpr_consent_text='   ')
        self.assertFalse(form.show_gdpr_consent)
        self.assertEqual(form.gdpr_consent_text, '')

    def test_presentational_fields_never_take_half_a_row(self):
        form = self._form(fields=[
            {'label': 'About you', 'field_type': 'section', 'is_required': False,
             'placeholder': '', 'help_text': '', 'options': [],
             'contact_field_mapping': '', 'width': 'half'},
            *self.PAYLOAD['fields'],
        ])
        section = form.fields.get(field_type='section')
        self.assertEqual(section.width, 'full')
