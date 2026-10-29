"""
Unlayer designs.

The editor loads `design_json`, so anything generated has to be wrapped as a
well-formed design or the template opens blank and the generation is lost.
The model writes the email HTML itself; this module only builds the document
around it.
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

_ID_ALPHABET = string.ascii_letters + string.digits + '_'


def _new_id() -> str:
    """An id in Unlayer's own style (10 characters, mixed case)."""
    return ''.join(random.choices(_ID_ALPHABET, k=10))


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


def _design(rows: list[dict], counters: dict, preheader: str) -> dict:
    """The document every generated template is wrapped in."""
    return {
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


def _html_content(html: str, index: int) -> dict:
    """Unlayer's own HTML tool, holding markup the model wrote itself."""
    return {
        'id': _new_id(),
        'type': 'html',
        'values': {
            **_common(f'u_content_html_{index}', 'u_content_html'),
            'html': html,
            'hideDesktop': False,
            '_languages': {},
        },
    }


def build_html_design(html: str, *, preheader: str = '') -> dict:
    """
    Wrap a complete email the model wrote as one Unlayer HTML block.

    The editor can only edit it as code, which is the trade made when the model
    writes the markup: it buys layouts the block vocabulary cannot express. The
    design still has to be well-formed or the editor refuses to open it at all.
    """
    counters = {'u_row': 1, 'u_column': 1, 'u_content_html': 1}
    rows = [_row(_html_content(html, 1), 1, 1)]
    return _design(rows, counters, preheader)
