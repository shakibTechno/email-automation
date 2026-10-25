"""
Seed the built-in landing page templates.

The template gallery is the first screen in the landing page workflow, and with
no system templates it offers a new organization exactly one choice: start from
an empty canvas. These give the categories something to show and the user
something to start from.

Usage:
    python manage.py seed_landing_page_templates
    python manage.py seed_landing_page_templates --clear

Idempotent: re-running updates the existing system templates in place rather
than creating duplicates. Only templates with `is_system=True` are touched, so
anything a user saved from their own page is left alone.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.landing_pages.models import LandingPageTemplate

# Markup follows the same Tailwind conventions as the builder's blocks, so the
# published page and the editor canvas render these identically.
HERO_LEAD_GEN = """
<section class="bg-gradient-to-br from-slate-900 to-slate-700 px-6 py-24 text-white">
  <div class="mx-auto max-w-3xl text-center">
    <h1 class="mb-6 text-5xl font-bold leading-tight">Get the guide that grows your list</h1>
    <p class="mb-8 text-xl text-slate-200">
      Join thousands of marketers who get practical, no-fluff tactics every week.
    </p>
    <a href="#signup" class="inline-block rounded-lg bg-white px-8 py-4 font-semibold text-slate-900">
      Get instant access
    </a>
  </div>
</section>
<section id="signup" class="px-6 py-20">
  <div class="mx-auto max-w-xl text-center">
    <h2 class="mb-4 text-3xl font-bold">Where should we send it?</h2>
    <p class="mb-8 text-gray-600">Add your form here from the Forms tab in the builder.</p>
  </div>
</section>
"""

WEBINAR = """
<section class="px-6 py-20">
  <div class="mx-auto grid max-w-6xl items-center gap-12 md:grid-cols-2">
    <div>
      <span class="mb-4 inline-block rounded-full bg-indigo-100 px-3 py-1 text-sm font-semibold text-indigo-700">
        Live webinar
      </span>
      <h1 class="mb-6 text-4xl font-bold leading-tight">
        Scaling your email programme without scaling your team
      </h1>
      <p class="mb-6 text-lg text-gray-600">
        A 45-minute session with live Q&amp;A. Can't make it? Register anyway and
        we'll send you the recording.
      </p>
      <ul class="mb-8 space-y-3 text-gray-700">
        <li>What to automate first, and what to leave alone</li>
        <li>The three metrics that actually predict revenue</li>
        <li>A teardown of two real lifecycle programmes</li>
      </ul>
    </div>
    <div class="rounded-xl bg-gray-50 p-8">
      <h2 class="mb-2 text-2xl font-bold">Save your seat</h2>
      <p class="text-gray-600">Drop your registration form here.</p>
    </div>
  </div>
</section>
"""

EBOOK = """
<section class="bg-amber-50 px-6 py-24">
  <div class="mx-auto grid max-w-5xl items-center gap-12 md:grid-cols-2">
    <div>
      <h1 class="mb-6 text-4xl font-bold leading-tight">
        The lifecycle email playbook
      </h1>
      <p class="mb-8 text-lg text-gray-700">
        68 pages of campaign structures, timing and copy you can lift straight
        into your own programme.
      </p>
      <div class="rounded-xl bg-white p-6 shadow-sm">
        <p class="text-gray-600">Add your download form here.</p>
      </div>
    </div>
    <div class="flex items-center justify-center">
      <div class="flex h-80 w-64 items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 text-center text-xl font-bold text-white shadow-xl">
        Your cover here
      </div>
    </div>
  </div>
</section>
"""

PRODUCT_LAUNCH = """
<section class="px-6 py-24 text-center">
  <div class="mx-auto max-w-3xl">
    <span class="mb-4 inline-block rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-700">
      Now available
    </span>
    <h1 class="mb-6 text-5xl font-bold leading-tight">Say hello to the new release</h1>
    <p class="mb-10 text-xl text-gray-600">
      Faster, calmer, and built on everything you told us was missing.
    </p>
    <a href="#" class="inline-block rounded-lg bg-gray-900 px-8 py-4 font-semibold text-white">
      See what's new
    </a>
  </div>
</section>
<section class="bg-gray-50 px-6 py-20">
  <div class="mx-auto grid max-w-5xl gap-8 md:grid-cols-3">
    <div class="rounded-xl bg-white p-6">
      <h3 class="mb-2 text-lg font-bold">Built for speed</h3>
      <p class="text-gray-600">Describe the first thing people will notice.</p>
    </div>
    <div class="rounded-xl bg-white p-6">
      <h3 class="mb-2 text-lg font-bold">Works with your stack</h3>
      <p class="text-gray-600">Describe how it fits what they already use.</p>
    </div>
    <div class="rounded-xl bg-white p-6">
      <h3 class="mb-2 text-lg font-bold">Priced to start</h3>
      <p class="text-gray-600">Describe the easiest way in.</p>
    </div>
  </div>
</section>
"""

EVENT = """
<section class="bg-slate-900 px-6 py-24 text-white">
  <div class="mx-auto max-w-4xl text-center">
    <p class="mb-4 text-lg font-semibold text-amber-400">14 March &middot; London</p>
    <h1 class="mb-6 text-5xl font-bold leading-tight">A one-day summit for growth teams</h1>
    <p class="mb-10 text-xl text-slate-300">
      Twelve speakers, two tracks, and the hallway track everyone actually comes for.
    </p>
    <a href="#register" class="inline-block rounded-lg bg-amber-400 px-8 py-4 font-semibold text-slate-900">
      Register now
    </a>
  </div>
</section>
<section id="register" class="px-6 py-20">
  <div class="mx-auto max-w-xl text-center">
    <h2 class="mb-4 text-3xl font-bold">Claim your ticket</h2>
    <p class="text-gray-600">Place your registration form here.</p>
  </div>
</section>
"""

COMING_SOON = """
<section class="flex min-h-screen items-center justify-center bg-gradient-to-br from-violet-600 to-indigo-700 px-6 text-white">
  <div class="mx-auto max-w-2xl text-center">
    <h1 class="mb-6 text-6xl font-bold leading-tight">Something good is coming</h1>
    <p class="mb-10 text-xl text-violet-100">
      We're nearly there. Leave your email and you'll be the first to know.
    </p>
    <div class="mx-auto max-w-md rounded-xl bg-white/10 p-6">
      <p class="text-violet-100">Add your signup form here.</p>
    </div>
  </div>
</section>
"""

THANK_YOU = """
<section class="flex min-h-screen items-center justify-center px-6 py-24">
  <div class="mx-auto max-w-2xl text-center">
    <div class="mx-auto mb-8 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-3xl text-emerald-600">
      &#10003;
    </div>
    <h1 class="mb-6 text-4xl font-bold">Thanks — that's all we need</h1>
    <p class="mb-10 text-lg text-gray-600">
      Check your inbox; it should land in the next couple of minutes. If it
      doesn't, look in your spam folder.
    </p>
    <a href="/" class="inline-block rounded-lg border px-6 py-3 font-semibold">
      Back to the site
    </a>
  </div>
</section>
"""

TEMPLATES = [
    {
        'name': 'Lead Magnet',
        'description': 'A headline, the promise, and one form. The default shape for list building.',
        'category': 'lead_generation',
        'html_content': HERO_LEAD_GEN,
    },
    {
        'name': 'Webinar Registration',
        'description': 'Session details beside the signup, with what attendees will learn.',
        'category': 'webinar',
        'html_content': WEBINAR,
    },
    {
        'name': 'E-book Download',
        'description': 'Cover art opposite the download form.',
        'category': 'ebook',
        'html_content': EBOOK,
    },
    {
        'name': 'Product Launch',
        'description': 'Announcement hero over a three-up feature row.',
        'category': 'product_launch',
        'html_content': PRODUCT_LAUNCH,
    },
    {
        'name': 'Event Registration',
        'description': 'Date, place and pitch, then the ticket form.',
        'category': 'event',
        'html_content': EVENT,
    },
    {
        'name': 'Coming Soon',
        'description': 'A single full-height panel for collecting interest before launch.',
        'category': 'coming_soon',
        'html_content': COMING_SOON,
    },
    {
        'name': 'Thank You',
        'description': 'The page to send people to after they convert.',
        'category': 'thank_you',
        'html_content': THANK_YOU,
    },
]


class Command(BaseCommand):
    help = 'Seed the built-in (system) landing page templates.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Remove the seeded system templates instead of creating them.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            deleted, _ = LandingPageTemplate.objects.filter(is_system=True).delete()
            self.stdout.write(self.style.SUCCESS(
                f'Removed {deleted} system template(s).'
            ))
            return

        created = updated = 0
        for spec in TEMPLATES:
            # System templates are global rather than per-organization, so the
            # name alone identifies them.
            _, was_created = LandingPageTemplate.objects.update_or_create(
                name=spec['name'],
                is_system=True,
                defaults={
                    'description': spec['description'],
                    'category': spec['category'],
                    'html_content': spec['html_content'].strip(),
                    'design_json': {},
                    'css_content': '',
                    'is_active': True,
                    'organization': None,
                },
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f'System templates: {created} created, {updated} updated.'
        ))
