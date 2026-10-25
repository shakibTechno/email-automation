"""
Give a free-plan subscription to organizations that have none.

Organizations created before subscription creation was wired to a signal have
no Subscription row, so billing endpoints 404 for them and check_usage_limit()
reports 'No active subscription' — which blocks every send once quota
enforcement is on. Run this once before enabling enforcement.

Safe to re-run: organizations that already have a subscription are skipped, and
initialize_subscription() is itself idempotent.
"""
from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.billing.models import Subscription
from apps.billing.services import BillingService


class Command(BaseCommand):
    help = 'Create a free-plan subscription for any organization lacking one.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would change without writing anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # all_objects, not objects: a soft-deleted organization still needs a
        # consistent billing record if it is ever restored.
        have = set(Subscription.objects.values_list('organization_id', flat=True))
        missing = [o for o in Organization.all_objects.all() if o.pk not in have]

        if not missing:
            self.stdout.write(self.style.SUCCESS(
                f'All {len(have)} organizations already have a subscription.'
            ))
            return

        self.stdout.write(
            f'{len(missing)} organization(s) without a subscription:'
        )
        for org in missing:
            self.stdout.write(f'  {org.name}  (plan={org.plan}, slug={org.slug})')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDry run — nothing written.'))
            return

        created, failed = 0, 0
        for org in missing:
            try:
                if BillingService.initialize_subscription(org, org.email or ''):
                    created += 1
                else:
                    # Returns None when no active free monthly Plan row exists.
                    failed += 1
                    self.stderr.write(self.style.ERROR(
                        f'  no free plan available — could not provision {org.name}'
                    ))
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f'  {org.name}: {exc}'))

        self.stdout.write(self.style.SUCCESS(f'\nCreated {created} subscription(s).'))
        if failed:
            self.stdout.write(self.style.ERROR(f'{failed} failed — see above.'))
