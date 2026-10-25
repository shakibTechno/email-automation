"""
Email template generation.

The model is asked for a short list of typed blocks — never for Unlayer's own
format, which it has no chance of producing correctly. `apps.ai_assistant.unlayer`
expands each block into a complete, schema-correct design so the template opens
in the editor as separate draggable items.
"""
import logging

from django.db import transaction

from apps.ai_assistant.unlayer import SUPPORTED_TYPES, build_design, build_html
from apps.templates.models import EmailTemplate

logger = logging.getLogger(__name__)

BLOCK_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['type', 'text', 'href', 'level'],
    'properties': {
        'type': {'type': 'string', 'enum': list(SUPPORTED_TYPES)},
        'text': {'type': 'string', 'description': 'The visible words. Plain text.'},
        'href': {
            'type': 'string',
            'description': 'Link target for a button. Empty for other types.',
        },
        'level': {
            'type': 'integer',
            'description': 'Heading level 1-3. Use 2 for anything that is not a heading.',
        },
    },
}

SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['name', 'subject', 'preheader', 'blocks'],
    'properties': {
        'name': {'type': 'string', 'description': 'Short internal name, 2-5 words.'},
        'subject': {'type': 'string', 'description': 'Subject line, under 60 characters.'},
        'preheader': {
            'type': 'string',
            'description': 'Preview text shown after the subject, under 90 characters.',
        },
        'blocks': {'type': 'array', 'items': BLOCK_SCHEMA},
    },
}

SYSTEM_PROMPT = """\
You write marketing emails as a sequence of blocks. Each block is one of:

  heading    - a short line of emphasis. `level` 1 for the opening line, 2 or 3 \
for section headings.
  paragraph  - one paragraph of body copy, plain text.
  button     - a call to action. `text` is the label, `href` the destination.

Every block needs all four keys. Set `href` to an empty string on anything that \
is not a button, and `level` to 2 on anything that is not a heading.

HOW TO WRITE IT

Open with the reader's situation, not your own announcement. One idea per \
paragraph, and keep paragraphs to two or three sentences — email is read in a \
narrow column, often on a phone.

Six to ten blocks is right for most emails. One button, placed after you have \
given the reader a reason to press it. If a second call to action genuinely \
helps, make it a text link inside a paragraph rather than a second button.

The subject line earns the open: concrete and specific, under 60 characters, no \
clickbait and no ALL CAPS. The preheader continues the subject rather than \
repeating it — together they are two lines of one thought.

Write plain text, not HTML or Markdown. No asterisks, no bullet characters, no \
emoji unless the described tone calls for it. Where you must invent a detail, \
keep it plainly generic so it reads as something to replace.

Do not write a footer, an unsubscribe line, or a physical address: the platform \
adds those when the email is sent.\
"""


def build_user_prompt(*, prompt: str, audience: str = '') -> str:
    parts = [f'Write a marketing email about:\n\n{prompt.strip()}']
    if audience.strip():
        parts.append(f'It is going to: {audience.strip()}')
    return '\n\n'.join(parts)


def validate(payload: dict) -> str | None:
    blocks = payload.get('blocks') or []
    usable = [
        b for b in blocks
        if (b.get('type') in SUPPORTED_TYPES and (b.get('text') or '').strip())
    ]
    if not usable:
        return 'The model returned no usable email content. Try rephrasing.'
    return None


@transaction.atomic
def create(job, payload: dict) -> EmailTemplate:
    blocks = payload.get('blocks') or []
    preheader = (payload.get('preheader') or '').strip()

    design, kept = build_design(blocks, preheader=preheader)
    html = build_html(blocks, preheader=preheader)

    if kept < len(blocks):
        logger.info(
            f'Generated email kept {kept} of {len(blocks)} blocks; '
            'the rest were an unsupported type or empty'
        )

    template = EmailTemplate.objects.create(
        organization=job.organization,
        name=(payload.get('name') or job.prompt)[:255].strip() or 'Untitled template',
        description=(job.prompt or '')[:500],
        category='custom',
        subject=(payload.get('subject') or '')[:255],
        design_json=design,
        html_content=html,
    )
    logger.info(f'Generated email template {template.id} with {kept} block(s)')
    return template
