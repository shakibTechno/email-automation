"""
Management command to create test data for development.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import Organization
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Create test organizations and users for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before creating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing test data...')
            # Clear test organizations and users
            Organization.objects.filter(name__startswith='Test').delete()
            User.objects.filter(email__contains='test').exclude(is_superuser=True).delete()
            self.stdout.write(self.style.SUCCESS('Test data cleared'))

        self.stdout.write('Creating test data...')

        # Create test organizations
        org_data = [
            {
                'name': 'Test Startup Inc',
                'email': 'contact@teststartup.com',
                'plan': 'starter',
            },
            {
                'name': 'Test Enterprise Corp',
                'email': 'contact@testenterprise.com',
                'plan': 'enterprise',
            },
        ]

        for org_info in org_data:
            org, created = Organization.objects.get_or_create(
                name=org_info['name'],
                defaults={
                    'email': org_info['email'],
                    'plan': org_info['plan'],
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created organization: {org.name}')
                )

                # Create users for this organization
                users_data = [
                    {
                        'email': f'owner@{org.slug}.com',
                        'first_name': 'Owner',
                        'last_name': 'User',
                        'role': 'owner',
                    },
                    {
                        'email': f'admin@{org.slug}.com',
                        'first_name': 'Admin',
                        'last_name': 'User',
                        'role': 'admin',
                    },
                    {
                        'email': f'member@{org.slug}.com',
                        'first_name': 'Member',
                        'last_name': 'User',
                        'role': 'member',
                    },
                ]

                for user_info in users_data:
                    user, user_created = User.objects.get_or_create(
                        email=user_info['email'],
                        defaults={
                            'first_name': user_info['first_name'],
                            'last_name': user_info['last_name'],
                            'organization': org,
                            'role': user_info['role'],
                            'is_active': True,
                            'is_email_verified': True,
                        }
                    )
                    if user_created:
                        user.set_password('testpass123')
                        user.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created user: {user.email} (password: testpass123)'
                            )
                        )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Organization already exists: {org.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('\nTest data creation complete!')
        )
        self.stdout.write('\nTest credentials:')
        self.stdout.write('Email: owner@test-startup-inc.com')
        self.stdout.write('Password: testpass123')
