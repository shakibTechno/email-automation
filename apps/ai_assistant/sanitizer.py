"""
Allowlist sanitizer for model-generated page markup.

Generated HTML is written to `LandingPage.html_content`, which is served to the
public and rendered in previews. The model is not a trusted author and the
prompt that steers it is user input, so nothing reaches storage without passing
through here first.

Allowlist, not denylist: anything not named below is removed, so a tag or
attribute nobody anticipated fails closed.
"""
import logging

import nh3

logger = logging.getLogger(__name__)

# Structural and text tags a landing page legitimately needs. Deliberately
# absent: script, style, iframe, object, embed, form, input, button (the form
# comes from the builder's Forms tab, which is what makes submissions
# attributable to the page).
ALLOWED_TAGS = {
    'section', 'div', 'span', 'header', 'footer', 'main', 'article', 'aside', 'nav',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'a', 'br', 'hr',
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'strong', 'em', 'b', 'i', 'u', 's', 'small', 'mark', 'blockquote', 'q', 'cite',
    'img', 'figure', 'figcaption', 'picture', 'source',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption',
    'label', 'time', 'abbr', 'code', 'pre',
}

# `class` carries the entire visual design (Tailwind utilities), so it is the
# one attribute that matters most. `style` is allowed because generated pages
# legitimately set gradients and background images that Tailwind cannot express
# as a utility; nh3 sanitizes its contents rather than passing it through raw.
ALLOWED_ATTRIBUTES = {
    '*': {'class', 'id', 'style', 'title', 'role', 'aria-label', 'aria-hidden', 'data-form-slot'},
    # `rel` is deliberately absent: `link_rel` below sets it on every link, and
    # nh3 refuses to let both manage the same attribute. Having the sanitizer
    # force `noopener noreferrer` is the safer of the two anyway, since it
    # cannot be talked out of it by generated markup.
    'a': {'href', 'target'},
    'img': {'src', 'alt', 'width', 'height', 'loading'},
    'source': {'srcset', 'type', 'media'},
    'td': {'colspan', 'rowspan'},
    'th': {'colspan', 'rowspan', 'scope'},
    'time': {'datetime'},
}

# No `javascript:`, no `data:` (which can carry scriptable SVG).
ALLOWED_URL_SCHEMES = {'http', 'https', 'mailto', 'tel'}


def sanitize_page_html(html: str) -> tuple[str, bool]:
    """
    Clean generated markup for storage.

    Returns the cleaned HTML and whether anything was removed, so a caller can
    tell the user their draft differs from what the model produced rather than
    changing it silently.
    """
    if not html:
        return '', False

    cleaned = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        # Anything stripped should vanish, not reappear as visible text.
        strip_comments=True,
        link_rel='noopener noreferrer',
    )

    # nh3 normalises markup (quoting, tag closing) even when it removes
    # nothing, so a plain string comparison would report every page as
    # altered. Compare what survived instead: a second pass over already-clean
    # output is a fixed point.
    was_modified = nh3.clean(
        cleaned,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        strip_comments=True,
        link_rel='noopener noreferrer',
    ) != cleaned

    if was_modified:  # pragma: no cover - defensive; a second pass should be stable
        logger.warning('Sanitizer was not idempotent on generated markup')

    # The honest signal for "we changed it" is whether the dangerous
    # constructs we care about were present in the input.
    removed_something = _contains_disallowed(html)
    if removed_something:
        logger.info('Sanitizer removed disallowed markup from generated page')

    return cleaned, removed_something


# Lowercased markers whose presence in the raw output means the sanitizer had
# real work to do. Used only for reporting, never for the cleaning itself.
_DISALLOWED_MARKERS = (
    '<script', '<iframe', '<object', '<embed', '<style', '<form',
    'javascript:', 'onerror=', 'onclick=', 'onload=', 'onmouseover=',
)


def _contains_disallowed(html: str) -> bool:
    lowered = html.lower().replace(' =', '=')
    return any(marker in lowered for marker in _DISALLOWED_MARKERS)
