"""
Email template generation.

The model returns a list of blocks. Most are typed — heading, paragraph, button
— and become Unlayer's own tools, so the reader can drag, edit and delete each
one in the editor. For anything the typed blocks cannot express, a hero band, a
two-column row, a bordered table, it returns an `html` block instead.

That mix is the point. An earlier version offered only the three typed blocks,
which made the vocabulary the ceiling: every generated email was three stacked
text styles because nothing else could be said. Replacing them wholesale with
one HTML blob fixed the ceiling and broke the editor, since the entire email
then became code. Here the cost is paid per block, by the parts that actually
need it.

No markup the model writes is trusted. `sanitize_email_html` is an allowlist and
runs over every html block before anything reaches storage.
"""
import logging
import re

from django.db import transaction

from apps.ai_assistant.sanitizer import sanitize_email_html
from apps.ai_assistant.unlayer import SUPPORTED_TYPES, build_design, build_html
from apps.templates.models import EmailTemplate

logger = logging.getLogger(__name__)

BLOCK_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['type', 'text', 'html', 'href', 'level'],
    'properties': {
        'type': {'type': 'string', 'enum': list(SUPPORTED_TYPES)},
        'text': {
            'type': 'string',
            'description': 'The visible words, plain text. Empty for an html block.',
        },
        'html': {
            'type': 'string',
            'description': (
                'Markup for an html block: table layout, inline styles, no '
                '<html>/<head>/<body>/<style>. Empty for every other type.'
            ),
        },
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
  html       - a band of markup you write yourself, for anything the three \
above cannot express.

Every block needs all five keys. Put your words in `text` and leave `html` \
empty, except on an html block, where `html` carries the markup and `text` is \
empty. Set `href` to an empty string on anything that is not a button, and \
`level` to 2 on anything that is not a heading.

WHEN TO USE AN HTML BLOCK

Prefer the typed blocks. They stay editable in the drag-and-drop editor, so the \
reader can rewrite a paragraph or change a button without touching code. An html \
block is editable only as code, so it costs the reader something — use it where \
it earns that.

It earns it for: a coloured hero band behind the opening line, two or three \
items side by side, a bordered box or table, a row of statistics, an image with \
a caption. Reach for it two or three times in an email, not for every block.

WRITING AN HTML BLOCK

Email HTML is not web HTML. It is read by clients whose rendering engines are \
twenty years apart.

Return a fragment, not a document: no <html>, <head>, <body>, <style>, <script> \
or comments. Lay out with nested <table> elements, never float, flex or grid, \
and give every table `role="presentation" cellpadding="0" cellspacing="0" \
border="0"`. The block is already inside a 600px column, so use `width="100%"`.

Every style must be inline on the element — a <style> block is stripped by Gmail \
and most webmail, so anything you put there is lost. Use hex colours, px sizes \
and a web-safe stack such as `-apple-system, 'Segoe UI', Arial, sans-serif`. \
Body copy at 15-16px with `line-height:1.6` and a dark grey like #333333; pure \
black on white is harsh on a phone.

Build a button inside an html block as a table cell with a background colour, \
padding and `border-radius`, holding an <a> styled `display:inline-block; \
color:#ffffff; text-decoration:none`. A styled <a> alone has no clickable area \
in Outlook.

Images need an explicit `width`, `alt` text and `style="display:block; border:0; \
max-width:100%; height:auto"`. Never put words only in an image: many clients \
block images by default, so the email has to read with every image missing. Use \
https://placehold.co/600x300 where an image is needed but none was given.

HOW TO WRITE IT

Open with the reader's situation, not your own announcement. One idea per \
paragraph, two or three sentences each — email is read in a narrow column, often \
on a phone.

Eight to fourteen blocks suits most emails. One primary button, placed after you \
have given the reader a reason to press it. If a second call to action genuinely \
helps, make it a text link inside a paragraph rather than a second button.

The subject line earns the open: concrete and specific, under 60 characters, no \
clickbait and no ALL CAPS. The preheader continues the subject rather than \
repeating it — together they are two lines of one thought.

Write plain text in `text`: no HTML, no Markdown, no asterisks, no bullet \
characters, no emoji unless the described tone calls for it. Where you must \
invent a detail, keep it plainly generic so it reads as something to replace.

Do not write a footer, an unsubscribe line, or a physical address: the platform \
adds those when the email is sent.\
"""


def build_user_prompt(*, prompt: str, audience: str = '') -> str:
    parts = [f'Write a marketing email about:\n\n{prompt.strip()}']
    if audience.strip():
        parts.append(f'It is going to: {audience.strip()}')
    return '\n\n'.join(parts)


def _body_of(block: dict) -> str:
    """The content of a block, wherever its type keeps it."""
    kind = (block.get('type') or '').strip()
    return ((block.get('html') if kind == 'html' else block.get('text')) or '').strip()


def _visible_text(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html or '')).strip()


def validate(payload: dict) -> str | None:
    blocks = payload.get('blocks') or []
    usable = [
        b for b in blocks
        if (b.get('type') in SUPPORTED_TYPES and _body_of(b))
    ]
    if not usable:
        return 'The model returned no usable email content. Try rephrasing.'
    # An email of nothing but empty markup renders as a blank message.
    if not any(_visible_text(_body_of(b)) for b in usable):
        return 'The model returned an email with no readable text. Try rephrasing.'
    return None


def _clean(blocks: list[dict]) -> tuple[list[dict], bool]:
    """Sanitize the markup in html blocks; leave typed blocks alone."""
    cleaned: list[dict] = []
    removed_any = False
    for block in blocks:
        if (block.get('type') or '').strip() != 'html':
            cleaned.append(block)
            continue
        html, removed = sanitize_email_html(block.get('html') or '')
        removed_any = removed_any or removed
        cleaned.append({**block, 'html': html})
    return cleaned, removed_any


@transaction.atomic
def create(job, payload: dict) -> EmailTemplate:
    blocks, removed = _clean(payload.get('blocks') or [])
    preheader = (payload.get('preheader') or '').strip()
    if removed:
        logger.info(
            f'Sanitizer removed disallowed markup from generated email for job {job.id}'
        )

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
