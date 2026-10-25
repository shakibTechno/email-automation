"""
Builds Unlayer designs from a simple list of typed blocks.

The email editor (`frontend/src/pages/templates/TemplateEditorPage.tsx`) only
ever calls `loadDesign(design_json)` — it never reads `html_content`. So a
generated template that carries only HTML opens as a blank canvas, and the
first save exports that blank design over the email. Generated email is
therefore a design_json problem.

Unlayer's format is closed and deep: every content block carries about twenty
`values` keys, ids follow a counter scheme that `_meta.htmlID` has to agree
with, and text is not HTML at all — it is a Lexical document under `textJson`.
Nothing about that is guessable, so the shapes below were read out of the
templates already in this database rather than invented, and the model is only
ever asked for `{type, text, href}`.
"""
import logging
import random
import string

logger = logging.getLogger(__name__)

# Matches the designs already stored by this Unlayer build.
SCHEMA_VERSION = 23

#: Block types this builder can emit. Deliberately narrow: these are the ones
#: with a verified shape that need no uploaded asset. Images need a real asset
#: URL plus dimensions and content type, so they stay something you add in the
#: editor, where the upload callback already exists.
SUPPORTED_TYPES = ('heading', 'paragraph', 'button')

_ID_ALPHABET = string.ascii_letters + string.digits + '_'


def _new_id() -> str:
    """An id in Unlayer's own style (10 characters, mixed case)."""
    return ''.join(random.choices(_ID_ALPHABET, k=10))


def _lexical(text: str, *, paragraph_type: str, inline_tool: bool = False) -> str:
    """
    One line of text as a Lexical document, serialized the way Unlayer stores it.

    `paragraph_type` differs per block: headings use `heading-paragraph`,
    paragraphs `paragraph`, and buttons `extended-paragraph`.
    """
    import json

    child = {
        'detail': 0,
        'format': 0,
        'mode': 'normal',
        'style': '',
        'text': text,
        'type': 'extended-text',
        'version': 1,
    }
    paragraph = {
        'children': [child],
        'format': '',
        'indent': 0,
        'type': paragraph_type,
        'version': 1,
        'textFormat': 0,
    }
    if inline_tool:
        paragraph['isInlineTool'] = True
    else:
        paragraph['textStyle'] = ''

    return json.dumps({
        'root': {
            'children': [paragraph],
            'format': '',
            'indent': 0,
            'type': 'root',
            'version': 1,
        }
    })


# Keys every content block carries regardless of type.
def _common(html_id: str, class_name: str) -> dict:
    return {
        'containerPadding': '10px',
        'anchor': '',
        'displayCondition': None,
        '_styleGuide': None,
        '_meta': {'htmlID': html_id, 'htmlClassNames': class_name},
        'selectable': True,
        'draggable': True,
        'duplicatable': True,
        'deletable': True,
        'hideable': True,
        'locked': False,
    }


_LINK_STYLE = {
    'inherit': True,
    'linkColor': '#0000ee',
    'linkHoverColor': '#0000ee',
    'linkUnderline': True,
    'linkHoverUnderline': True,
}


def _heading(text: str, level: int, index: int) -> dict:
    level = level if level in (1, 2, 3) else 2
    return {
        'id': _new_id(),
        'type': 'heading',
        'values': {
            **_common(f'u_content_heading_{index}', 'u_content_heading'),
            'textJson': _lexical(text, paragraph_type='heading-paragraph'),
            'headingType': f'h{level}',
            'fontSize': {1: '28px', 2: '22px', 3: '18px'}[level],
            'textAlign': 'left',
            'lineHeight': '140%',
            'linkStyle': dict(_LINK_STYLE),
            '_languages': {},
        },
    }


def _paragraph(text: str, index: int) -> dict:
    return {
        'id': _new_id(),
        'type': 'paragraph',
        'values': {
            **_common(f'u_content_paragraph_{index}', 'u_content_paragraph'),
            'textJson': _lexical(text, paragraph_type='paragraph'),
            'fontSize': '14px',
            'textAlign': 'left',
            'lineHeight': '160%',
            'linkStyle': dict(_LINK_STYLE),
            'hideDesktop': False,
            '_languages': {},
        },
    }


def _button(text: str, href: str, index: int) -> dict:
    return {
        'id': _new_id(),
        'type': 'button',
        'values': {
            **_common(f'u_content_button_{index}', 'u_content_button'),
            'textJson': _lexical(
                text, paragraph_type='extended-paragraph', inline_tool=True,
            ),
            'href': {
                'name': 'web',
                'values': {'href': href, 'target': '_blank'},
                'attrs': {'href': '{{href}}', 'target': '{{target}}'},
            },
            'buttonColors': {
                'color': '#FFFFFF',
                'backgroundColor': '#0879A1',
                'hoverColor': '#FFFFFF',
                'hoverBackgroundColor': '#0879A1',
            },
            'size': {'autoWidth': True, 'width': '100%'},
            'fontSize': '14px',
            'lineHeight': '120%',
            'textAlign': 'center',
            'padding': '10px 20px',
            'border': {},
            'borderRadius': '4px',
            'hideDesktop': False,
        },
    }


def _row(content: dict, row_index: int, column_index: int) -> dict:
    return {
        'id': _new_id(),
        'cells': [1],
        'columns': [{
            'id': _new_id(),
            'contents': [content],
            'values': {
                'backgroundColor': '',
                'padding': '0px',
                'border': {},
                'borderRadius': '0px',
                '_meta': {
                    'htmlID': f'u_column_{column_index}',
                    'htmlClassNames': 'u_column',
                },
                'deletable': True,
                'locked': False,
            },
        }],
        'values': {
            'displayCondition': None,
            'columns': False,
            '_styleGuide': None,
            'backgroundColor': '',
            'columnsBackgroundColor': '',
            'backgroundImage': {
                'url': '', 'fullWidth': True, 'repeat': 'no-repeat',
                'size': 'custom', 'position': 'center',
                'customPosition': ['50%', '50%'],
            },
            'padding': '0px',
            'anchor': '',
            'hideDesktop': False,
            '_meta': {'htmlID': f'u_row_{row_index}', 'htmlClassNames': 'u_row'},
            'selectable': True,
            'draggable': True,
            'duplicatable': True,
            'deletable': True,
            'hideable': True,
            'locked': False,
        },
    }


def build_design(blocks: list[dict], *, preheader: str = '') -> tuple[dict, int]:
    """
    Turn `[{type, text, href?, level?}, ...]` into a complete Unlayer design.

    Returns the design and how many blocks survived. Unrecognised or empty
    blocks are skipped rather than guessed at — one fewer block beats a design
    the editor silently refuses to load.
    """
    rows: list[dict] = []
    counters = {'u_row': 0, 'u_column': 0}

    for raw in blocks:
        kind = (raw.get('type') or '').strip()
        text = (raw.get('text') or '').strip()
        if kind not in SUPPORTED_TYPES or not text:
            logger.info(f'Skipping generated email block of type {kind!r}')
            continue

        key = f'u_content_{kind}'
        counters[key] = counters.get(key, 0) + 1
        counters['u_row'] += 1
        counters['u_column'] += 1

        if kind == 'heading':
            content = _heading(text, int(raw.get('level') or 2), counters[key])
        elif kind == 'paragraph':
            content = _paragraph(text, counters[key])
        else:
            content = _button(text, (raw.get('href') or '#').strip(), counters[key])

        rows.append(_row(content, counters['u_row'], counters['u_column']))

    design = {
        'counters': counters,
        'body': {
            'id': _new_id(),
            'rows': rows,
            'headers': [],
            'footers': [],
            'values': {
                '_styleGuide': None,
                'popupPosition': 'center',
                'popupWidth': '600px',
                'popupHeight': 'auto',
                'borderRadius': '10px',
                'contentAlign': 'center',
                'contentVerticalAlign': 'center',
                'contentWidth': '600px',
                'fontFamily': {
                    'label': 'Arial', 'value': "arial,helvetica,sans-serif",
                },
                'textColor': '#000000',
                'popupBackgroundColor': '#FFFFFF',
                'popupBackgroundImage': {
                    'url': '', 'fullWidth': True, 'repeat': 'no-repeat',
                    'size': 'cover', 'position': 'center',
                },
                'popupOverlay_backgroundColor': 'rgba(0, 0, 0, 0.1)',
                'popupCloseButton_position': 'top-right',
                'popupCloseButton_backgroundColor': '#DDDDDD',
                'popupCloseButton_iconColor': '#000000',
                'popupCloseButton_borderRadius': '0px',
                'popupCloseButton_margin': '0px',
                'popupCloseButton_action': {
                    'name': 'close_popup',
                    'attrs': {'onClick': "document.querySelector('.u-popup-container').style.display = 'none';"},
                },
                'language': {},
                'backgroundColor': '#F7F8F9',
                'preheaderText': preheader,
                'linkStyle': dict(_LINK_STYLE),
                'backgroundImage': {
                    'url': '', 'fullWidth': True, 'repeat': 'no-repeat',
                    'size': 'custom', 'position': 'center',
                },
                'accessibilityTitle': '',
                '_meta': {'htmlID': 'u_body', 'htmlClassNames': 'u_body'},
            },
        },
        'schemaVersion': SCHEMA_VERSION,
    }
    return design, len(rows)


def build_html(blocks: list[dict], *, preheader: str = '') -> str:
    """
    A plain email rendering of the same blocks.

    Unlayer regenerates `html_content` from the design the first time the
    template is saved, so this only has to be correct enough that a template
    nobody opens still sends something sensible.
    """
    from django.utils.html import escape

    parts = []
    if preheader:
        parts.append(
            f'<div style="display:none;max-height:0;overflow:hidden;">'
            f'{escape(preheader)}</div>'
        )

    for raw in blocks:
        kind = (raw.get('type') or '').strip()
        text = escape((raw.get('text') or '').strip())
        if kind not in SUPPORTED_TYPES or not text:
            continue
        if kind == 'heading':
            level = raw.get('level') if raw.get('level') in (1, 2, 3) else 2
            size = {1: '28px', 2: '22px', 3: '18px'}[level]
            parts.append(
                f'<h{level} style="font-size:{size};line-height:140%;'
                f'margin:10px;">{text}</h{level}>'
            )
        elif kind == 'paragraph':
            parts.append(
                f'<p style="font-size:14px;line-height:160%;margin:10px;">{text}</p>'
            )
        else:
            href = escape((raw.get('href') or '#').strip())
            parts.append(
                f'<div style="text-align:center;margin:10px;">'
                f'<a href="{href}" style="display:inline-block;padding:10px 20px;'
                f'background:#0879A1;color:#FFFFFF;border-radius:4px;'
                f'text-decoration:none;font-size:14px;">{text}</a></div>'
            )

    body = '\n'.join(parts)
    return (
        '<!doctype html><html><body style="margin:0;background:#F7F8F9;">'
        '<div style="max-width:600px;margin:0 auto;background:#FFFFFF;'
        'font-family:arial,helvetica,sans-serif;color:#000000;">'
        f'{body}</div></body></html>'
    )
