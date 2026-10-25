"""
Form generation.

The simplest of the generators and the most valuable: no HTML, no sanitizer, a
closed set of field types, and a direct line to whether the form actually works
— `contact_field_mapping` is what turns a submission into a Contact, so a form
that collects an email and maps nothing produces submissions and no leads.
"""
import logging

from django.db import transaction

from apps.forms.models import Form, FormField

logger = logging.getLogger(__name__)

# Built from the model's own choices so the two cannot drift apart.
VALID_FIELD_TYPES = {value for value, _ in FormField.FIELD_TYPE_CHOICES}
VALID_MAPPINGS = {value for value, _ in FormField.CONTACT_FIELD_MAPPING_CHOICES if value}

# Types that are decoration rather than input, and so are never required and
# never map to a contact field.
PRESENTATIONAL_TYPES = {'section', 'divider'}
# Types that are meaningless without choices to offer.
CHOICE_TYPES = {'dropdown', 'radio'}

SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['name', 'description', 'submit_button_text', 'success_message', 'fields'],
    'properties': {
        'name': {'type': 'string', 'description': 'Short internal name, 2-5 words.'},
        'description': {'type': 'string', 'description': 'One sentence shown above the form.'},
        'submit_button_text': {'type': 'string', 'description': 'Button label, 1-4 words.'},
        'success_message': {
            'type': 'string',
            'description': 'Shown after a successful submission.',
        },
        'fields': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': [
                    'label', 'field_type', 'is_required',
                    'placeholder', 'help_text', 'options', 'contact_field_mapping',
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
its way to your inbox"), not merely that the form was received.\
"""


def build_user_prompt(*, prompt: str, audience: str = '') -> str:
    parts = [f'Create a lead capture form for:\n\n{prompt.strip()}']
    if audience.strip():
        parts.append(f'The people filling it in are: {audience.strip()}')
    return '\n\n'.join(parts)


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

    return {
        'label': label,
        'field_type': field_type,
        'is_required': bool(raw.get('is_required')) and not presentational,
        'placeholder': ('' if presentational else (raw.get('placeholder') or ''))[:255],
        'help_text': (raw.get('help_text') or '')[:500],
        'options': options,
        'contact_field_mapping': '' if presentational else mapping,
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

    form = Form.objects.create(
        organization=job.organization,
        name=(payload.get('name') or job.prompt)[:255].strip() or 'Untitled form',
        description=(payload.get('description') or '')[:1000],
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

    logger.info(f'Generated form {form.id} with {len(cleaned)} field(s)')
    return form
