"""
Landing page generation.

The prompt and schema live in `apps.ai_assistant.prompts`, which predates this
package; this module holds the part that turns a generated payload into a
LandingPage, so the service can treat every kind of generation the same way.
"""
import logging

from django.db import transaction

from apps.ai_assistant.prompts import PAGE_SCHEMA, SYSTEM_PROMPT as _SYSTEM_PROMPT
from apps.ai_assistant.prompts import build_user_prompt as _build_user_prompt
from apps.ai_assistant.sanitizer import sanitize_page_html
from apps.landing_pages.models import LandingPage

logger = logging.getLogger(__name__)

SCHEMA = PAGE_SCHEMA
SYSTEM_PROMPT = _SYSTEM_PROMPT
build_user_prompt = _build_user_prompt

# Markup appended when the model omits the capture point. Matches what the
# prompt asks for, so the builder's Forms tab drops into it the same way either
# route produced it.
FORM_SLOT_HTML = (
    '<section class="py-16 px-4">'
    '<div data-form-slot="true" class="mx-auto max-w-xl rounded-xl border-2 '
    'border-dashed border-gray-300 p-8 text-center text-gray-500">'
    'Drop your form here from the Forms tab</div>'
    '</section>'
)


def ensure_form_slot(html: str) -> str:
    """
    Make sure the draft has somewhere to put the lead capture form.

    The prompt asks for this marker, but smaller models — a self-hosted one in
    particular — do not always obey. A landing page with no capture point
    cannot convert anyone, and the conversion tracking keys off a form being
    present, so this is added deterministically rather than left to the model's
    discretion.
    """
    if not html.strip() or 'data-form-slot' in html:
        return html
    return html + FORM_SLOT_HTML


def prepare(payload: dict) -> tuple[dict, bool]:
    """
    Clean the generated markup before anything is written.

    Returns the payload with sanitized HTML and whether the sanitizer removed
    anything, so the UI can say the draft was altered.
    """
    html, was_sanitized = sanitize_page_html(payload.get('html', ''))
    html = ensure_form_slot(html)
    return {**payload, 'html': html}, was_sanitized


def validate(payload: dict) -> str | None:
    """Return a user-facing reason this payload is unusable, or None."""
    if not (payload.get('html') or '').strip():
        return 'The model returned no usable page content. Try rephrasing.'
    return None


@transaction.atomic
def create(job, payload: dict) -> LandingPage:
    # The model names the page, but it is not trusted to be the right length or
    # to be present at all.
    name = (payload.get('name') or job.prompt)[:255].strip() or 'Untitled page'

    page = LandingPage.objects.create(
        organization=job.organization,
        name=name,
        status='draft',
        html_content=payload.get('html', ''),
        # Left empty on purpose: with no design_json the builder imports
        # html_content into editable components, which is the whole point of
        # generating flat top-level sections.
        design_json={},
        css_content='',
        seo_title=(payload.get('seo_title') or '')[:70],
        seo_description=(payload.get('seo_description') or '')[:160],
        created_by=job.created_by,
    )
    logger.info(f'Generated landing page {page.id}')
    return page
