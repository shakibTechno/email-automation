"""
Email template generation.

The model writes the email's HTML itself. An earlier version asked for a short
list of typed blocks — heading, paragraph, button — which was safe but could
only ever produce three stacked text styles; every generated email looked the
same because the vocabulary was the ceiling.

What it costs: the template opens in the editor as a single HTML block, so it
is editable as code rather than as draggable pieces. That is the trade. It buys
hero sections, multi-column layouts, tables and real styling.

Nothing the model writes is trusted. `sanitize_email_html` is an allowlist, and
it runs before anything reaches storage.
"""
import logging
import re

from django.db import transaction

from apps.ai_assistant.sanitizer import sanitize_email_html
from apps.ai_assistant.unlayer import build_html_design
from apps.templates.models import EmailTemplate

logger = logging.getLogger(__name__)

SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['name', 'subject', 'preheader', 'html'],
    'properties': {
        'name': {'type': 'string', 'description': 'Short internal name, 2-5 words.'},
        'subject': {'type': 'string', 'description': 'Subject line, under 60 characters.'},
        'preheader': {
            'type': 'string',
            'description': 'Preview text shown after the subject, under 90 characters.',
        },
        'html': {
            'type': 'string',
            'description': (
                'The email body as HTML. Table-based layout, all styles inline, '
                '600px wide. No <html>, <head>, <body> or <style> tags.'
            ),
        },
    },
}

SYSTEM_PROMPT = """\
You write marketing emails as HTML. Email HTML is not web HTML — it is read by \
clients whose rendering engines are twenty years apart, and the rules below are \
what make the difference between a design that holds and one that collapses in \
Outlook.

STRUCTURE

Return the body only. No <html>, <head>, <body>, <style>, <script> or comments: \
the platform supplies the document around what you write.

Lay out with nested <table> elements, never with float, flex or grid. Give every \
table `role="presentation" cellpadding="0" cellspacing="0" border="0"`. Wrap the \
whole email in one table of `width="600"` with a `max-width:600px` inline style, \
centred inside a full-width table that carries the page background colour.

STYLING

Every style must be inline on the element. A <style> block is stripped by Gmail \
and most webmail, so anything you put there is simply lost.

Use hex colours, px sizes and a web-safe stack such as \
`-apple-system, 'Segoe UI', Arial, sans-serif`. Body copy at 15-16px with \
`line-height:1.6` and a dark grey like #333333 — pure black on white is harsh on \
a phone. Headings 22-30px and bold. Keep content padding around 24-32px.

Build a button as a table cell with a background colour, padding and \
`border-radius`, holding an <a> styled `display:inline-block; color:#ffffff; \
text-decoration:none`. A styled <a> alone has no clickable area in Outlook.

Images need an explicit `width`, `alt` text and `style="display:block; border:0; \
max-width:100%; height:auto"`. Never put words only in an image: many clients \
block images by default, so the email has to read with every image missing. \
Use https://placehold.co/600x300 where an image is needed but none was given.

WHAT TO WRITE

Open with the reader's situation, not your own announcement. One idea per \
paragraph, two or three sentences each — email is read in a narrow column, often \
on a phone. One primary call to action, placed after you have given a reason to \
press it.

The subject line earns the open: concrete, specific, under 60 characters, no \
clickbait and no ALL CAPS. The preheader continues the subject rather than \
repeating it — together they are two lines of one thought.

Where you must invent a detail, keep it plainly generic so it reads as something \
to replace. Do not write a footer, an unsubscribe line or a physical address: \
the platform adds those when the email is sent.\
"""


def build_user_prompt(*, prompt: str, audience: str = '') -> str:
    parts = [f'Write a marketing email about:\n\n{prompt.strip()}']
    if audience.strip():
        parts.append(f'It is going to: {audience.strip()}')
    return '\n\n'.join(parts)


# Enough markup to be an email rather than a sentence the model returned when it
# misread the request.
_MIN_TEXT_LENGTH = 40


def _visible_text(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html or '')).strip()


def validate(payload: dict) -> str | None:
    html = (payload.get('html') or '').strip()
    if not html:
        return 'The model returned no email content. Try rephrasing.'
    if '<' not in html:
        return 'The model returned plain text rather than HTML. Try again.'
    if len(_visible_text(html)) < _MIN_TEXT_LENGTH:
        return 'The model returned an email with almost no readable text. Try rephrasing.'
    return None


@transaction.atomic
def create(job, payload: dict) -> EmailTemplate:
    preheader = (payload.get('preheader') or '').strip()
    html, removed = sanitize_email_html(payload.get('html') or '')
    if removed:
        logger.info(
            f'Sanitizer removed disallowed markup from generated email for job {job.id}'
        )

    template = EmailTemplate.objects.create(
        organization=job.organization,
        name=(payload.get('name') or job.prompt)[:255].strip() or 'Untitled template',
        description=(job.prompt or '')[:500],
        category='custom',
        subject=(payload.get('subject') or '')[:255],
        # The editor loads design_json, so the HTML has to be wrapped as a
        # design or the template opens blank and the generation is lost.
        design_json=build_html_design(html, preheader=preheader),
        html_content=html,
    )
    logger.info(f'Generated email template {template.id} ({len(html)} chars of HTML)')
    return template
