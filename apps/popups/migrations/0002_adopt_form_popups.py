"""
Move popups out of the forms table and into their own.

Popups shipped as `Form.form_type != 'inline'` with a `display_rules` blob.
They are now their own object, and the form they came from becomes the form
they embed -- so every existing popup keeps its fields, its styling and its
behaviour, and gains a title, an image and a call to action it could not have
had before.

The old columns go in the same migration as the copy. Leaving them would mean
two places answering "is this a popup" and "when does it show", and the two
would disagree the first time anyone edited one.
"""
from django.db import migrations

# The blob used one key for the trigger and the frequency together; the new
# model separates them, because "when does it appear" and "how often may it
# appear again" are different questions that were being answered in one place.
TRIGGER_MAP = {
    'time': 'time',
    'scroll': 'scroll',
    'exit_intent': 'exit_intent',
    'click': 'click',
}
TYPE_MAP = {
    'popup': 'modal',
    'slide_in': 'slide_in',
    # Renamed to match what the rest of the industry calls it, and what the
    # acceptance criteria asked for.
    'top_bar': 'floating_bar',
}


def adopt(apps, schema_editor):
    Form = apps.get_model('forms', 'Form')
    Popup = apps.get_model('popups', 'Popup')

    for form in Form.objects.exclude(form_type='inline').iterator():
        rules = form.display_rules or {}
        overlay = rules.get('overlay') or {}

        if rules.get('showOnce'):
            frequency = {'mode': 'once_per_visitor', 'days': 7}
        elif rules.get('cooldownDays'):
            frequency = {'mode': 'every_n_days', 'days': rules['cooldownDays']}
        else:
            frequency = {'mode': 'every_visit', 'days': 7}

        Popup.objects.create(
            organization_id=form.organization_id,
            name=form.name,
            popup_type=TYPE_MAP.get(form.form_type, 'modal'),
            # An active form becomes a published popup; anything else becomes a
            # draft. Nothing that was live stops being live, and nothing that
            # was not starts.
            status='published' if form.status == 'active' else 'draft',
            title=(form.branding or {}).get('headerText', '') or '',
            description=form.description or '',
            form=form,
            design={
                'backgroundColor': (form.styling or {}).get('backgroundColor', '#ffffff'),
                'textColor': (form.styling or {}).get('textColor', '#0f172a'),
                'headingColor': (form.styling or {}).get('textColor', '#0f172a'),
                'fontFamily': (form.styling or {}).get(
                    'fontFamily', 'Inter, system-ui, sans-serif'),
                'borderRadius': overlay.get('borderRadius', '12px'),
                'padding': '28px',
                'maxWidth': overlay.get('width', '440px'),
                'backdrop': overlay.get('backdrop', True),
                'backdropColor': overlay.get(
                    'backdropColor', 'rgba(15, 23, 42, 0.55)'),
                'position': rules.get('position', 'center'),
                'primaryButton': {
                    'backgroundColor': (form.styling or {}).get('primaryColor', '#4f46e5'),
                    'textColor': '#ffffff',
                    'borderRadius': overlay.get('borderRadius', '8px'),
                    'fullWidth': False,
                },
                'closeButton': {'show': True, 'color': '#64748b', 'delaySeconds': 0},
                'image': {'position': 'none', 'height': '160px'},
            },
            triggers={
                'type': TRIGGER_MAP.get(rules.get('trigger'), 'time'),
                'delaySeconds': rules.get('delaySeconds', 5),
                'scrollPercent': rules.get('scrollPercent', 50),
                'pageVisitCount': 2,
                'inactivitySeconds': 30,
                'clickSelector': rules.get('clickSelector', ''),
            },
            targeting={
                'includeUrls': rules.get('includeUrls', []),
                'excludeUrls': rules.get('excludeUrls', []),
                'devices': rules.get('devices', ['desktop', 'mobile']),
                'visitorType': 'any',
                'referrers': [],
                'utm': {},
            },
            frequency=frequency,
            created_by_id=form.created_by_id,
        )

    # The forms stay, as the capture half of the popups that now own them.
    Form.objects.exclude(form_type='inline').update(form_type='inline')


def unadopt(apps, schema_editor):
    """
    Reversible only in the sense that the popups go away again.

    The forms they embedded stay as inline forms, because turning them back
    into popups would need the display_rules column this migration removes.
    """
    apps.get_model('popups', 'Popup').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('popups', '0001_initial'),
        ('forms', '0005_form_display_rules'),
    ]

    operations = [
        migrations.RunPython(adopt, unadopt),
    ]

    # The forms side of this -- dropping display_rules and narrowing
    # FORM_TYPE_CHOICES to 'inline' -- lives in the forms app, which is the
    # only place that may alter its own table. It depends on this migration,
    # so the copy always happens before the columns go.
