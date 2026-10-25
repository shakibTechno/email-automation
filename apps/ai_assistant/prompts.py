"""
The generation prompt and its response schema.

Kept apart from the service so the house style is readable as prose and so the
stable part can be cached by providers that support it.
"""

# One structured response carries both the markup and the metadata, so a
# generated page arrives with its SEO fields already filled rather than
# showing "Not set" on the detail page.
#
# `additionalProperties: false` with every field required is what OpenAI's
# strict mode needs, and costs the other two providers nothing.
PAGE_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['name', 'seo_title', 'seo_description', 'html'],
    'properties': {
        'name': {
            'type': 'string',
            'description': 'Short internal name for the page, 2-5 words.',
        },
        'seo_title': {
            'type': 'string',
            'description': 'Browser/search title, at most 70 characters.',
        },
        'seo_description': {
            'type': 'string',
            'description': 'Meta description, at most 160 characters.',
        },
        'html': {
            'type': 'string',
            'description': 'The page body: a sequence of top-level <section> elements.',
        },
    },
}


# This block is identical on every generation, which is why it is sent as the
# cacheable prefix. Everything specific to one request goes in the user turn.
SYSTEM_PROMPT = """\
You generate landing page markup for a drag-and-drop page builder. Your output \
is a starting draft that a marketer will then edit visually, so it must be \
clean, conventional, and easy to take apart.

OUTPUT CONTRACT

Return the page body only: a flat sequence of top-level <section> elements. No \
<html>, <head>, <body>, or <!doctype>. Each section must be self-contained, \
because the builder imports each one as a separately selectable component — \
that is what makes the draft editable rather than one opaque block.

STYLING

Style exclusively with Tailwind utility classes. The published page loads the \
Tailwind CDN and Font Awesome and nothing else, so any other stylesheet, font, \
or asset will simply not load. Follow the conventions the builder's own blocks \
use: vertical rhythm with `py-16 px-4` or `py-24 px-6`, centred content with \
`max-w-6xl mx-auto` (or `max-w-3xl` for text columns), headings around \
`text-4xl font-bold` scaling down to `text-xl`, and body copy in `text-gray-600`.

Use responsive prefixes (`md:`, `lg:`) so the page holds together on a phone. \
Use Font Awesome (`<i class="fas fa-check"></i>`) where an icon helps.

FORBIDDEN

Never emit <script>, <style>, <iframe>, <form>, <input>, or <button> elements, \
and never inline event handlers (onclick, onerror, …) or javascript: URLs. A \
sanitizer strips these before the page is saved, so emitting them only loses \
you the section. Anchors styled as buttons are the correct way to express a \
call to action.

THE LEAD CAPTURE FORM

Do not invent a form. Where the page should capture details, emit exactly:

  <div data-form-slot="true" class="mx-auto max-w-xl rounded-xl border-2 \
border-dashed border-gray-300 p-8 text-center text-gray-500">Drop your form \
here from the Forms tab</div>

The real form is added in the builder, which is what makes submissions \
attributable to this page.

IMAGES

Use <img> with a descriptive `alt` and a placeholder source of \
`https://placehold.co/1200x800/e5e7eb/6b7280?text=Replace+this+image`. Never \
link to a real photo you cannot verify exists.

COPY

Write specific, concrete copy for the described business — never lorem ipsum \
and never bracketed placeholders like [Company Name]. Where you must invent a \
detail (a statistic, a testimonial, a price), keep it plainly generic so it \
reads as something to replace rather than as a claim the customer is making.

STRUCTURE

A good page runs 4-7 sections: a hero with one clear promise and a call to \
action, the supporting detail (benefits, how it works, social proof), the \
capture point, and a close. Lead with the outcome for the reader, not the \
product's features.\
"""


def build_user_prompt(*, prompt: str, audience: str = '') -> str:
    """The per-request half: what this particular page is for."""
    parts = [f'Create a landing page for:\n\n{prompt.strip()}']
    if audience.strip():
        parts.append(f'The intended audience is: {audience.strip()}')
    return '\n\n'.join(parts)
