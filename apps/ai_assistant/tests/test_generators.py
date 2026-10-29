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
    The model writes the email's HTML. The block vocabulary it replaced could
    only produce three stacked text styles, which is why every generated email
    looked alike.
    """

    HTML = (
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'border="0" style="max-width:600px">'
        '<tr><td bgcolor="#1a1a2e" align="center" style="padding:32px">'
        '<h1 style="color:#ffffff;font-size:28px;margin:0">Stop guessing</h1>'
        '</td></tr>'
        '<tr><td style="padding:24px">'
        '<p style="font-size:16px;line-height:1.6;color:#333333">'
        'Your bounce rate is telling you something specific.</p>'
        '</td></tr>'
        '<tr><td align="center" style="padding:0 24px 32px">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        '<tr><td bgcolor="#4f46e5" style="border-radius:6px;padding:14px 28px">'
        '<a href="https://example.com/webinar" '
        'style="display:inline-block;color:#ffffff;text-decoration:none">'
        'Save my seat</a></td></tr></table>'
        '</td></tr></table>'
    )

    PAYLOAD = {
        'name': 'Bounce rate webinar',
        'subject': 'Stop landing in spam',
        'preheader': 'A 45 minute session on deliverability.',
        'html': HTML,
    }

    def test_creates_a_template_the_editor_can_load(self):
        job = self._job(GenerationJob.KIND_EMAIL_TEMPLATE)
        template = email_templates.create(job, self.PAYLOAD)

        self.assertEqual(template.subject, 'Stop landing in spam')
        self.assertEqual(template.design_json['schemaVersion'], SCHEMA_VERSION)
        # One HTML block. The editor loads design_json, so wrapping it is what
        # stops the template opening blank.
        rows = template.design_json['body']['rows']
        self.assertEqual(len(rows), 1)
        content = rows[0]['columns'][0]['contents'][0]
        self.assertEqual(content['type'], 'html')
        self.assertIn('Stop guessing', content['values']['html'])
        self.assertIn('Stop guessing', template.html_content)

    def test_the_preheader_reaches_the_design(self):
        job = self._job(GenerationJob.KIND_EMAIL_TEMPLATE)
        template = email_templates.create(job, self.PAYLOAD)
        self.assertEqual(
            template.design_json['body']['values']['preheaderText'],
            'A 45 minute session on deliverability.',
        )

    def test_table_layout_and_inline_styles_survive(self):
        """
        Email layout is tables and presentational attributes. A sanitizer tuned
        for landing pages would strip exactly what makes the email render.
        """
        job = self._job(GenerationJob.KIND_EMAIL_TEMPLATE)
        template = email_templates.create(job, self.PAYLOAD)

        for fragment in ('cellpadding="0"', 'bgcolor="#1a1a2e"', 'width="600"',
                         'align="center"', 'style="max-width:600px"'):
            self.assertIn(fragment, template.html_content, fragment)

    def test_script_is_removed_from_a_generated_email(self):
        job = self._job(GenerationJob.KIND_EMAIL_TEMPLATE)
        template = email_templates.create(job, {
            **self.PAYLOAD,
            'html': self.HTML + '<script>fetch("https://evil.test")</script>',
        })

        self.assertNotIn('<script', template.html_content)
        self.assertNotIn('evil.test', template.html_content)
        self.assertIn('Stop guessing', template.html_content)

    def test_rejects_output_that_is_not_an_email(self):
        self.assertIsNotNone(email_templates.validate({'html': ''}))
        self.assertIsNotNone(
            email_templates.validate({'html': 'Sorry, I cannot help with that.'}),
            'plain prose is not an email',
        )
        self.assertIsNotNone(
            email_templates.validate({'html': '<div><span></span></div>'}),
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
