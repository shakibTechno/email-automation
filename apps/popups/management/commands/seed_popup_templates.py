"""
Seed the system pop-up templates.

A management command rather than a data migration, following
`seed_landing_page_templates`, so the set can change without a schema change
and can be re-run after editing the copy below.

Each template carries content, design intent and a trigger together. One that
only set colours would save nobody any time — the work in a popup is deciding
what it says and when it interrupts.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.popups.models import Popup, PopupTemplate, default_design

TEMPLATES = [
    {
        'name': 'Newsletter signup',
        'description': 'Ask for an email after the reader has got something out of the page.',
        'category': 'newsletter',
        'popup_type': Popup.TYPE_MODAL,
        'wants_form': True,
        'content': {
            'title': 'Get the good stuff',
            'description': 'One email a month. Unsubscribe whenever you like.',
            'ctaText': 'Subscribe',
        },
        # Halfway down: long enough to mean they are reading, early enough that
        # they have not finished and left.
        'triggers': {'type': 'scroll', 'scrollPercent': 50},
        'design': {'position': 'center', 'primary': '#4f46e5'},
    },
    {
        'name': 'Discount offer',
        'description': 'A code in exchange for an address, shown once the visitor is browsing.',
        'category': 'discount',
        'popup_type': Popup.TYPE_MODAL,
        'wants_form': True,
        'content': {
            'title': '10% off your first order',
            'description': 'Tell us where to send the code.',
            'ctaText': 'Send my code',
        },
        'triggers': {'type': 'time', 'delaySeconds': 12},
        'design': {'position': 'center', 'primary': '#059669'},
    },
    {
        'name': 'Exit offer',
        'description': 'One last offer as the pointer heads for the tab bar.',
        'category': 'exit_offer',
        'popup_type': Popup.TYPE_MODAL,
        'wants_form': True,
        'content': {
            'title': 'Before you go',
            'description': 'Leave your email and we will hold this for you.',
            'ctaText': 'Hold it for me',
        },
        # Exit intent needs a mouse; the snippet falls back to this delay on
        # touch devices rather than never showing it.
        'triggers': {'type': 'exit_intent', 'delaySeconds': 25},
        'design': {'position': 'center', 'primary': '#b91c1c'},
    },
    {
        'name': 'Lead magnet',
        'description': 'Trade a guide or a template for a work address.',
        'category': 'lead_magnet',
        'popup_type': Popup.TYPE_SLIDE_IN,
        'wants_form': True,
        'content': {
            'title': 'The guide, free',
            'description': 'Twelve pages on what actually moves the number.',
            'ctaText': 'Send it to me',
        },
        # A slide-in earns its place by not interrupting, so it waits for the
        # second page rather than the first.
        'triggers': {'type': 'page_visit', 'pageVisitCount': 2},
        'design': {'position': 'bottom_right', 'primary': '#0ea5e9'},
    },
    {
        'name': 'Announcement bar',
        'description': 'Say one thing and link somewhere. No form, no fields.',
        'category': 'announcement',
        'popup_type': Popup.TYPE_FLOATING_BAR,
        'wants_form': False,
        'content': {
            'title': 'We are at the summit this week — come and say hello',
            'ctaText': 'Book a slot',
        },
        'triggers': {'type': 'time', 'delaySeconds': 2},
        'design': {'position': 'top', 'primary': '#0f172a'},
    },
]


class Command(BaseCommand):
    help = 'Create or update the built-in pop-up templates.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete the system templates instead of seeding them.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            # Only the system ones. An organization's own saved templates are
            # theirs and are never touched by a deploy.
            count, _ = PopupTemplate.objects.filter(is_system=True).delete()
            self.stdout.write(self.style.WARNING(f'Removed {count} system template(s).'))
            return

        for spec in TEMPLATES:
            design = default_design()
            design['position'] = spec['design']['position']
            design['primaryButton'] = {
                **design['primaryButton'],
                'backgroundColor': spec['design']['primary'],
            }
            if spec['popup_type'] == Popup.TYPE_FLOATING_BAR:
                # A bar is a line of text, not a card.
                design['maxWidth'] = '100%'
                design['padding'] = '14px 20px'
                design['borderRadius'] = '0px'
                design['backdrop'] = False

            _, created = PopupTemplate.objects.update_or_create(
                name=spec['name'], is_system=True,
                defaults={
                    'description': spec['description'],
                    'category': spec['category'],
                    'popup_type': spec['popup_type'],
                    'content': spec['content'],
                    'design': design,
                    'triggers': spec['triggers'],
                    'wants_form': spec['wants_form'],
                    'is_active': True,
                    'organization': None,
                },
            )
            verb = 'Created' if created else 'Updated'
            self.stdout.write(f'  {verb}: {spec["name"]}')

        self.stdout.write(self.style.SUCCESS(f'{len(TEMPLATES)} template(s) ready.'))
