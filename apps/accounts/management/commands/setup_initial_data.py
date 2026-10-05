"""
Management command to set up initial data for production.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import Organization
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up initial data for production'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial data...')

        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING('Superuser already exists. Skipping setup.')
            )
            return

        # Get admin credentials from environment
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'changeme123')
        admin_org = os.getenv('ADMIN_ORG', 'Admin Organization')

        # Create admin organization
        org = Organization.objects.create(
            name=admin_org,
            email=admin_email,
            plan='enterprise',
        )
        self.stdout.write(
            self.style.SUCCESS(f'Created organization: {org.name}')
        )

        # Create superuser
        admin = User.objects.create_superuser(
            email=admin_email,
            password=admin_password,
            first_name='Admin',
            last_name='User',
            organization=org,
        )
        self.stdout.write(
            self.style.SUCCESS(f'Created superuser: {admin.email}')
        )

        self.stdout.write(
            self.style.SUCCESS('\nInitial setup complete!')
        )
        self.stdout.write(
            self.style.WARNING(
                f'\nIMPORTANT: Change the admin password!'
            )
        )
