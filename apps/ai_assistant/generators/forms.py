"""
Form generation.

Fills the whole builder, not just its first step: fields and settings, then the
design — colours, typography, button and input styling, layout and branding —
so a generated form arrives looking considered rather than as a default-grey
stack someone still has to style.

The model is asked for design *intent*, not for forty CSS values. It picks a
primary colour, a style and a column count; everything concrete is derived from
those here. Asking a model to fill in `focusRingColor` directly produces a
schema nobody can satisfy and values that are subtly wrong; deriving them means
the output is always valid and still looks deliberate.

`contact_field_mapping` is the one that decides whether the form works at all:
it is what turns a submission into a Contact, so a form that collects an email
and maps nothing produces submissions and no leads.
"""
import logging
import re

from django.db import transaction

from apps.forms.models import (
    Form, FormField, default_branding, default_layout, default_styling,
)

logger = logging.getLogger(__name__)

# Built from the model's own choices so the two cannot drift apart.
VALID_FIELD_TYPES = {value for value, _ in FormField.FIELD_TYPE_CHOICES}
VALID_MAPPINGS = {value for value, _ in FormField.CONTACT_FIELD_MAPPING_CHOICES if value}

# Types that are decoration rather than input, and so are never required and
# never map to a contact field.
PRESENTATIONAL_TYPES = {'section', 'divider'}
# Types that are meaningless without choices to offer.
CHOICE_TYPES = {'dropdown', 'radio'}
VALID_WIDTHS = {value for value, _ in FormField.WIDTH_CHOICES}

# How a named style becomes concrete values. The model chooses the name; these
# are the parts it would get wrong.
STYLE_PRESETS = {
    'minimal': {
        'borderRadius': '4px', 'borderWidth': '1px', 'padding': '24px',
        'inputPadding': '10px 12px', 'buttonPadding': '10px 20px',
        'buttonFontWeight': '500', 'fullWidthButton': False,
    },
    'rounded': {
        'borderRadius': '12px', 'borderWidth': '1px', 'padding': '32px',
        'inputPadding': '12px 16px', 'buttonPadding': '12px 24px',
        'buttonFontWeight': '600', 'fullWidthButton': True,
    },
    'bold': {
        'borderRadius': '6px', 'borderWidth': '2px', 'padding': '32px',
        'inputPadding': '12px 14px', 'buttonPadding': '14px 28px',
        'buttonFontWeight': '700', 'fullWidthButton': True,
    },
    'classic': {
        'borderRadius': '2px', 'borderWidth': '1px', 'padding': '24px',
        'inputPadding': '10px 12px', 'buttonPadding': '10px 24px',
        'buttonFontWeight': '500', 'fullWidthButton': False,
    },
}
DEFAULT_STYLE = 'minimal'
_HEX = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': [
        'name', 'description', 'submit_button_text', 'success_message', 'fields',
        'header_text', 'footer_text', 'primary_color', 'style', 'columns',
        'show_gdpr_consent', 'gdpr_consent_text',
    ],
    'properties': {
        'name': {'type': 'string', 'description': 'Short internal name, 2-5 words.'},
        'description': {'type': 'string', 'description': 'One sentence shown above the form.'},
        'submit_button_text': {'type': 'string', 'description': 'Button label, 1-4 words.'},
        'success_message': {
            'type': 'string',
            'description': 'Shown after a successful submission.',
        },
        'header_text': {
            'type': 'string',
            'description': 'Headline above the form, 3-7 words. Empty for none.',
        },
        'footer_text': {
            'type': 'string',
            'description': 'Small reassurance under the button. Empty for none.',
        },
        'primary_color': {
            'type': 'string',
            'description': 'Brand colour as a hex code, e.g. #3b82f6. Used for the '
                           'button and focus states.',
        },
        'style': {
            'type': 'string',
            'enum': sorted(STYLE_PRESETS),
            'description': 'Overall feel of the form.',
        },
        'columns': {
            'type': 'integer',
            'description': '1 for a single column, 2 to place short fields side by side.',
        },
        'show_gdpr_consent': {
            'type': 'boolean',
            'description': 'Whether a consent checkbox is shown before submitting.',
        },
        'gdpr_consent_text': {
            'type': 'string',
            'description': 'Consent wording. Empty when show_gdpr_consent is false.',
        },
        'fields': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': [
                    'label', 'field_type', 'is_required', 'placeholder',
                    'help_text', 'options', 'contact_field_mapping', 'width',
                ],
                'properties': {
                    'label': {'type': 'string'},
                    'field_type': {
                        'type': 'string',
                        'enum': sorted(VALID_FIELD_TYPES),
                    },
                    'is_required': {'type': 'boolean'},
                    'placeholder': {'type': 'string'},
                    'help_text': {'type': 'string'},
                    'options': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Choices for dropdown/radio. Empty otherwise.',
                    },
                    'contact_field_mapping': {
                        'type': 'string',
                        'enum': [''] + sorted(VALID_MAPPINGS),
                        'description': 'Which contact field this fills. Empty for none.',
                    },
                    'width': {
                        'type': 'string',
                        'enum': sorted(VALID_WIDTHS),
                        'description': 'How much of the row this field takes. '
                                       '"full" unless the form is two columns.',
                    },
                },
            },
        },
    },
}

SYSTEM_PROMPT = """\
You design lead capture forms. Your output is a working form that a marketer \
will then adjust, so favour the shortest form that does the job.

RULES

Every form must include an email field, typed `email` and mapped to the contact \
field `email`. That mapping is what turns a submission into a contact in the \
CRM; without it the form collects replies that go nowhere.

Map every field that corresponds to a contact field — first_name, last_name, \
email, phone, company, job_title. Leave `contact_field_mapping` empty for \
anything that does not correspond to one, such as a question about budget or \
timeline.

Keep forms short. Each extra field costs conversions. Three to five input \
fields suits most cases; ask for a phone number or a job title only when the \
described use genuinely needs it.

Mark a field required only when the form is useless without it. Email is \
usually the only truly required field.

`dropdown` and `radio` fields must list their `options`. Every other type must \
leave `options` empty.

`section` and `divider` are layout only: never required, never mapped, and they \
carry no placeholder.

Write the `success_message` to say what happens next ("Thanks — the guide is on \
its way to your inbox"), not merely that the form was received.\n\nCONSENT\n\nSet `show_gdpr_consent` when the form gathers contact details in order to market\nto someone later, which is most lead capture. Write `gdpr_consent_text` as one\nplain sentence saying who is contacting them and what about - not a link to a\npolicy, and never pre-ticked wording like "by submitting you agree". Leave it\nempty when consent is off.\n\nDESIGN\n\nYou also choose how the form looks.\n\n`primary_color` is a hex code used for the button and the focus state. Pick one\nthat suits what is described - a colour the described brand would plausibly use,\nnot always blue. Keep it dark enough that white button text stays readable.\n\n`style` is the overall feel: `minimal` for sharp edges and restraint, `rounded`\nfor soft and friendly, `bold` for heavy borders and a large button, `classic`\nfor square and conservative.\n\n`columns` is 1 unless the form has four or more input fields and some are short\nenough to pair - first and last name, city and postcode. When you use 2, set\n`width` to `half` on exactly the fields that should share a row and `full` on\nthe rest. With 1 column every field is `full`.\n\n`header_text` is a headline above the form, promising what the reader gets.\n`footer_text` is a small line under the button that lowers the barrier - how\noften you will email, that it is free, that they can unsubscribe. Either may be\nempty, but a form with both converts better than one with neither.\n"""


def build_user_prompt(*, prompt: str, audience: str = '') -> str:
    parts = [f'Create a lead capture form for:\n\n{prompt.strip()}']
    if audience.strip():
        parts.append(f'The people filling it in are: {audience.strip()}')
    return '\n\n'.join(parts)


def _hex_or(value: str, fallback: str) -> str:
    """A hex colour the builder can store, or the fallback."""
    value = (value or '').strip()
    if not _HEX.match(value):
        return fallback
    if len(value) == 4:  # #abc -> #aabbcc, so arithmetic below has 6 digits
        value = '#' + ''.join(c * 2 for c in value[1:])
    return value.lower()


def _shade(hex_color: str, factor: float) -> str:
    """Darken (factor < 1) or lighten a hex colour, for hover and focus states."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    scaled = (
        min(255, max(0, round(channel * factor))) for channel in (r, g, b)
    )
    return '#%02x%02x%02x' % tuple(scaled)


def _design(payload: dict) -> tuple[dict, dict, dict]:
    """
    Turn the model's design intent into the three blobs the builder stores.

    Starts from the model defaults and overrides, so a key the builder expects
    is never missing: the design panel reads these directly and a hole in them
    renders as an empty input rather than a sensible default.
    """
    primary = _hex_or(payload.get('primary_color'), '#3b82f6')
    preset = STYLE_PRESETS.get(
        (payload.get('style') or '').strip().lower(), STYLE_PRESETS[DEFAULT_STYLE]
    )

    styling = default_styling()
    styling.update({
        'primaryColor': primary,
        'borderRadius': preset['borderRadius'],
        'padding': preset['padding'],
    })
    styling['buttonStyle'] = {
        **styling['buttonStyle'],
        'backgroundColor': primary,
        # A hover that is merely the same colour reads as a dead control.
        'hoverBackgroundColor': _shade(primary, 0.85),
        'borderRadius': preset['borderRadius'],
        'fontWeight': preset['buttonFontWeight'],
        'padding': preset['buttonPadding'],
        'fullWidth': preset['fullWidthButton'],
    }
    styling['inputStyle'] = {
        **styling['inputStyle'],
        'borderWidth': preset['borderWidth'],
        'borderRadius': preset['borderRadius'],
        'padding': preset['inputPadding'],
        'focusBorderColor': primary,
        # 20% alpha, the same convention as the stored default.
        'focusRingColor': f'{primary}33',
    }

    branding = default_branding()
    branding.update({
        'headerText': (payload.get('header_text') or '').strip()[:255],
        'footerText': (payload.get('footer_text') or '').strip()[:255],
    })

    columns = payload.get('columns')
    columns = columns if columns in (1, 2, 3) else 1
    layout = default_layout()
    layout.update({
        'columns': columns,
        # A two-column form needs room for two fields to sit side by side.
        'maxWidth': '640px' if columns > 1 else layout['maxWidth'],
    })
    return styling, branding, layout


def _clean_field(raw: dict, order: int) -> dict | None:
    """
    Turn one generated field into something the model will accept, or None.

    Anything whose type is not in the model's own choices is dropped rather
    than coerced — a guess about what the model meant is worse than a form with
    one fewer field.
    """
    label = (raw.get('label') or '').strip()[:255]
    field_type = (raw.get('field_type') or '').strip()

    if not label or field_type not in VALID_FIELD_TYPES:
        logger.info(f'Dropping generated field {label!r} with type {field_type!r}')
        return None

    mapping = (raw.get('contact_field_mapping') or '').strip()
    if mapping not in VALID_MAPPINGS:
        mapping = ''

    options = [str(o).strip() for o in (raw.get('options') or []) if str(o).strip()]
    if field_type in CHOICE_TYPES and not options:
        logger.info(f'Dropping choice field {label!r} that came back with no options')
        return None
    if field_type not in CHOICE_TYPES:
        options = []

    presentational = field_type in PRESENTATIONAL_TYPES

    width = (raw.get('width') or '').strip()
    if width not in VALID_WIDTHS or presentational:
        # A section header or divider spanning half a row looks like a bug.
        width = 'full'

    return {
        'label': label,
        'field_type': field_type,
        'is_required': bool(raw.get('is_required')) and not presentational,
        'placeholder': ('' if presentational else (raw.get('placeholder') or ''))[:255],
        'help_text': (raw.get('help_text') or '')[:500],
        'options': options,
        'contact_field_mapping': '' if presentational else mapping,
        'width': width,
        'order': order,
    }


def _ensure_mapped_email(fields: list[dict]) -> list[dict]:
    """
    Guarantee the form can produce a lead.

    A form with no email field, or with one that maps to nothing, collects
    submissions that never become contacts. Rather than fail the generation
    over it, the email field is repaired or added.
    """
    for field in fields:
        if field['contact_field_mapping'] == 'email':
            field['is_required'] = True
            return fields

    # An email-typed field that simply was not mapped is the common case.
    for field in fields:
        if field['field_type'] == 'email':
            field['contact_field_mapping'] = 'email'
            field['is_required'] = True
            logger.info('Mapped a generated email field that came back unmapped')
            return fields

    logger.info('Generated form had no email field; adding one')
    return [{
        'label': 'Email',
        'field_type': 'email',
        'is_required': True,
        'placeholder': 'you@example.com',
        'help_text': '',
        'options': [],
        'contact_field_mapping': 'email',
        'width': 'full',
        'order': 0,
    }] + [{**f, 'order': f['order'] + 1} for f in fields]


@transaction.atomic
def create(job, payload: dict) -> Form:
    """Build the form and its fields from a generated payload."""
    raw_fields = payload.get('fields') or []
    cleaned = [
        field for field in (
            _clean_field(raw, order) for order, raw in enumerate(raw_fields)
        ) if field
    ]
    cleaned = _ensure_mapped_email(cleaned)

    styling, branding, layout = _design(payload)
    consent = bool(payload.get('show_gdpr_consent'))
    consent_text = (payload.get('gdpr_consent_text') or '').strip()
    if consent and not consent_text:
        # The checkbox renders either way; unlabelled it asks for agreement to
        # nothing, which is worse than not asking.
        consent = False
        logger.info('Generated form asked for consent with no wording; turning it off')

    form = Form.objects.create(
        organization=job.organization,
        name=(payload.get('name') or job.prompt)[:255].strip() or 'Untitled form',
        description=(payload.get('description') or '')[:1000],
        styling=styling,
        branding=branding,
        layout=layout,
        show_gdpr_consent=consent,
        gdpr_consent_text=consent_text if consent else '',
        # Inactive, which is this model's only "not live yet" state: the public
        # endpoint serves active forms only, so a generated form is reviewed
        # before anyone can submit to it.
        status='inactive',
        form_type='inline',
        submit_button_text=(payload.get('submit_button_text') or 'Submit')[:50],
        success_message=(
            payload.get('success_message') or 'Thank you for your submission!'
        ),
        created_by=job.created_by,
    )

    FormField.objects.bulk_create([
        FormField(form=form, **field) for field in cleaned
    ])

    logger.info(
        f'Generated form {form.id} with {len(cleaned)} field(s), '
        f'{layout["columns"]} column(s), primary {styling["primaryColor"]}'
    )
    return form
