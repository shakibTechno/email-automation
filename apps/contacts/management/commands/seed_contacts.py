"""
Management command to seed test contacts.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import Organization
from apps.contacts.models import Contact, Tag, ContactTag
from faker import Faker
import random


class Command(BaseCommand):
    help = 'Seed database with test contacts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of contacts to create (default: 50)'
        )
        parser.add_argument(
            '--organization',
            type=str,
            help='Organization slug to create contacts for'
        )

    def handle(self, *args, **options):
        count = options['count']
        org_slug = options.get('organization')

        # Get organization
        if org_slug:
            try:
                organization = Organization.objects.get(slug=org_slug)
            except Organization.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Organization with slug "{org_slug}" not found')
                )
                return
        else:
            # Get first organization
            organization = Organization.objects.first()
            if not organization:
                self.stdout.write(
                    self.style.ERROR('No organizations found. Please create one first.')
                )
                return

        self.stdout.write(f'Creating {count} contacts for organization: {organization.name}')

        fake = Faker()

        # Create tags first
        tags = []
        tag_data = [
            {'name': 'Customer', 'color': 'blue'},
            {'name': 'Lead', 'color': 'green'},
            {'name': 'VIP', 'color': 'purple'},
            {'name': 'Newsletter', 'color': 'orange'},
            {'name': 'Partner', 'color': 'yellow'},
            {'name': 'Inactive', 'color': 'gray'},
        ]

        for tag_info in tag_data:
            tag, created = Tag.objects.get_or_create(
                organization=organization,
                name=tag_info['name'],
                defaults={'color': tag_info['color']}
            )
            tags.append(tag)
            if created:
                self.stdout.write(f'  Created tag: {tag.name}')

        # Create contacts
        engagement_levels = ['high', 'medium', 'low', 'none']
        sources = ['manual', 'import', 'api', 'form', 'integration']

        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for i in range(count):
                email = fake.email()

                # Check if contact already exists
                if Contact.objects.filter(
                    organization=organization,
                    email=email
                ).exists():
                    skipped_count += 1
                    continue

                contact = Contact.objects.create(
                    organization=organization,
                    email=email,
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    phone=fake.phone_number()[:20],
                    company=fake.company(),
                    job_title=fake.job(),
                    lead_score=random.randint(0, 100),
                    engagement_level=random.choice(engagement_levels),
                    is_subscribed=random.choice([True, True, True, False]),  # 75% subscribed
                    is_verified=random.choice([True, False]),
                    source=random.choice(sources),
                    custom_fields={
                        'industry': fake.bs(),
                        'website': fake.url(),
                        'notes': fake.text(max_nb_chars=100)
                    }
                )

                # Add random tags
                num_tags = random.randint(0, 3)
                for tag in random.sample(tags, min(num_tags, len(tags))):
                    ContactTag.objects.create(contact=contact, tag=tag)

                created_count += 1

                if (i + 1) % 10 == 0:
                    self.stdout.write(f'  Created {i + 1}/{count} contacts...')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} contacts '
                f'(skipped {skipped_count} duplicates)'
            )
        )
        self.stdout.write(f'Organization: {organization.name}')
