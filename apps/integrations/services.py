"""
Services for the integrations app.
"""
import logging
import random
from django.db import transaction
from django.utils import timezone

from .models import AnalyticsIntegration, SocialIntegration, LeadSyncLog

logger = logging.getLogger(__name__)


class AnalyticsIntegrationService:
    """Service for managing analytics tracking integrations."""

    @staticmethod
    def get_integrations(organization):
        """Return all analytics integrations for the organization."""
        return AnalyticsIntegration.objects.filter(organization=organization)

    @staticmethod
    def upsert_integration(organization, provider, tracking_id, is_enabled=True, settings=None):
        """Create or update an analytics integration by org + provider."""
        defaults = {
            'tracking_id': tracking_id,
            'is_enabled': is_enabled,
            'settings': settings or {},
        }
        integration, created = AnalyticsIntegration.objects.update_or_create(
            organization=organization,
            provider=provider,
            defaults=defaults,
        )
        return integration

    @staticmethod
    def delete_integration(organization, provider):
        """Delete an analytics integration by org + provider."""
        deleted_count, _ = AnalyticsIntegration.objects.filter(
            organization=organization,
            provider=provider,
        ).delete()
        return deleted_count > 0

    @staticmethod
    def get_active_tracking_codes(organization):
        """Return all enabled analytics integrations as a list of dicts."""
        integrations = AnalyticsIntegration.objects.filter(
            organization=organization,
            is_enabled=True,
        )
        return [
            {
                'provider': integration.provider,
                'tracking_id': integration.tracking_id,
                'settings': integration.settings,
            }
            for integration in integrations
        ]


class SocialIntegrationService:
    """Service for managing social platform integrations."""

    PLATFORMS = [choice[0] for choice in SocialIntegration.PLATFORM_CHOICES]

    @staticmethod
    def get_integrations(organization):
        """
        List all social integrations for the organization.
        If fewer than 2 records exist, create defaults for missing platforms.
        """
        existing = SocialIntegration.objects.filter(organization=organization)
        existing_platforms = set(existing.values_list('platform', flat=True))

        for platform in SocialIntegrationService.PLATFORMS:
            if platform not in existing_platforms:
                SocialIntegration.objects.create(
                    organization=organization,
                    platform=platform,
                    status='disconnected',
                )

        return SocialIntegration.objects.filter(organization=organization)

    @staticmethod
    @transaction.atomic
    def demo_connect(organization, platform, user):
        """Connect an integration in demo mode."""
        platform_labels = dict(SocialIntegration.PLATFORM_CHOICES)
        platform_label = platform_labels.get(platform, platform)

        integration, created = SocialIntegration.objects.update_or_create(
            organization=organization,
            platform=platform,
            defaults={
                'status': 'connected',
                'is_demo': True,
                'external_account_name': f'Demo {platform_label} Account',
                'external_account_id': f'demo_{platform}_123',
                'connected_by': user,
                'field_mapping': {
                    'email': 'email',
                    'first_name': 'first_name',
                    'last_name': 'last_name',
                },
            },
        )
        return integration

    @staticmethod
    @transaction.atomic
    def disconnect(organization, platform):
        """Disconnect a social integration, clearing tokens and account info."""
        try:
            integration = SocialIntegration.objects.get(
                organization=organization,
                platform=platform,
            )
        except SocialIntegration.DoesNotExist:
            return None

        integration.status = 'disconnected'
        integration.access_token = ''
        integration.refresh_token = ''
        integration.token_expires_at = None
        integration.external_account_id = ''
        integration.external_account_name = ''
        integration.is_demo = False
        integration.save(update_fields=[
            'status', 'access_token', 'refresh_token', 'token_expires_at',
            'external_account_id', 'external_account_name', 'is_demo',
            'updated_at',
        ])
        return integration

    @staticmethod
    def update_credentials(integration, credentials_data):
        """Store API credentials on the integration."""
        integration.credentials = {
            'app_id': credentials_data['app_id'],
            'app_secret': credentials_data['app_secret'],
            'page_id': credentials_data.get('page_id', ''),
            'organization_id': credentials_data.get('organization_id', ''),
        }
        integration.save(update_fields=['credentials', 'updated_at'])
        return integration

    @staticmethod
    @transaction.atomic
    def connect(organization, platform, user):
        """Connect an integration using stored API credentials (non-demo)."""
        platform_labels = dict(SocialIntegration.PLATFORM_CHOICES)
        platform_label = platform_labels.get(platform, platform)

        try:
            integration = SocialIntegration.objects.get(
                organization=organization,
                platform=platform,
            )
        except SocialIntegration.DoesNotExist:
            return None

        creds = integration.credentials or {}
        if not creds.get('app_id') or not creds.get('app_secret'):
            raise ValueError('API credentials are required. Save your App ID and App Secret first.')

        # Derive account name from credentials
        account_name = creds.get('page_id') or creds.get('organization_id') or creds.get('app_id', '')
        integration.status = 'connected'
        integration.is_demo = False
        integration.connected_by = user
        integration.external_account_name = f'{platform_label} ({account_name})'
        integration.external_account_id = creds.get('app_id', '')

        if not integration.field_mapping:
            integration.field_mapping = {
                'email': 'email',
                'first_name': 'first_name',
                'last_name': 'last_name',
            }

        integration.save(update_fields=[
            'status', 'is_demo', 'connected_by',
            'external_account_name', 'external_account_id',
            'field_mapping', 'updated_at',
        ])
        return integration

    @staticmethod
    def update_settings(integration, data):
        """Update sync settings for an integration."""
        update_fields = ['updated_at']

        if 'auto_sync' in data:
            integration.auto_sync = data['auto_sync']
            update_fields.append('auto_sync')

        if 'sync_interval_minutes' in data:
            integration.sync_interval_minutes = data['sync_interval_minutes']
            update_fields.append('sync_interval_minutes')

        if 'field_mapping' in data:
            integration.field_mapping = data['field_mapping']
            update_fields.append('field_mapping')

        if 'default_tag' in data:
            integration.default_tag_id = data['default_tag']
            update_fields.append('default_tag')

        integration.save(update_fields=update_fields)
        return integration


# Seed data for demo lead generation
DEMO_LEADS = [
    {
        'first_name': 'Alice',
        'last_name': 'Johnson',
        'email': 'alice@techcorp.io',
        'company': 'TechCorp',
        'job_title': 'Marketing Director',
        'phone': '+1-555-0101',
    },
    {
        'first_name': 'Bob',
        'last_name': 'Smith',
        'email': 'bob@acmeinc.com',
        'company': 'Acme Inc',
        'job_title': 'Sales Manager',
        'phone': '+1-555-0102',
    },
    {
        'first_name': 'Carol',
        'last_name': 'Williams',
        'email': 'carol@startupxyz.com',
        'company': 'StartupXYZ',
        'job_title': 'CEO',
        'phone': '+1-555-0103',
    },
    {
        'first_name': 'David',
        'last_name': 'Brown',
        'email': 'david@globalmedia.net',
        'company': 'Global Media',
        'job_title': 'Content Strategist',
        'phone': '+1-555-0104',
    },
    {
        'first_name': 'Emily',
        'last_name': 'Davis',
        'email': 'emily@brightfuture.co',
        'company': 'Bright Future',
        'job_title': 'Head of Growth',
        'phone': '+1-555-0105',
    },
    {
        'first_name': 'Frank',
        'last_name': 'Miller',
        'email': 'frank@digitalhub.io',
        'company': 'Digital Hub',
        'job_title': 'Product Manager',
        'phone': '+1-555-0106',
    },
    {
        'first_name': 'Grace',
        'last_name': 'Wilson',
        'email': 'grace@innovatech.com',
        'company': 'InnovaTech',
        'job_title': 'VP of Marketing',
        'phone': '+1-555-0107',
    },
    {
        'first_name': 'Henry',
        'last_name': 'Moore',
        'email': 'henry@cloudnine.io',
        'company': 'Cloud Nine',
        'job_title': 'CTO',
        'phone': '+1-555-0108',
    },
    {
        'first_name': 'Ivy',
        'last_name': 'Taylor',
        'email': 'ivy@nextstep.co',
        'company': 'NextStep',
        'job_title': 'Business Development Lead',
        'phone': '+1-555-0109',
    },
    {
        'first_name': 'Jack',
        'last_name': 'Anderson',
        'email': 'jack@bluewavetech.com',
        'company': 'BlueWave Tech',
        'job_title': 'Engineering Manager',
        'phone': '+1-555-0110',
    },
    {
        'first_name': 'Karen',
        'last_name': 'Thomas',
        'email': 'karen@peakperform.net',
        'company': 'Peak Performance',
        'job_title': 'HR Director',
        'phone': '+1-555-0111',
    },
    {
        'first_name': 'Leo',
        'last_name': 'Jackson',
        'email': 'leo@rocketlaunch.io',
        'company': 'Rocket Launch',
        'job_title': 'Founder',
        'phone': '+1-555-0112',
    },
    {
        'first_name': 'Maria',
        'last_name': 'White',
        'email': 'maria@greenleaf.co',
        'company': 'GreenLeaf',
        'job_title': 'Operations Manager',
        'phone': '+1-555-0113',
    },
    {
        'first_name': 'Nathan',
        'last_name': 'Harris',
        'email': 'nathan@datastream.com',
        'company': 'DataStream',
        'job_title': 'Data Analyst',
        'phone': '+1-555-0114',
    },
    {
        'first_name': 'Olivia',
        'last_name': 'Martin',
        'email': 'olivia@sparkdigital.io',
        'company': 'Spark Digital',
        'job_title': 'Creative Director',
        'phone': '+1-555-0115',
    },
    {
        'first_name': 'Paul',
        'last_name': 'Garcia',
        'email': 'paul@visionaryinc.com',
        'company': 'Visionary Inc',
        'job_title': 'Account Executive',
        'phone': '+1-555-0116',
    },
    {
        'first_name': 'Quinn',
        'last_name': 'Martinez',
        'email': 'quinn@agileworks.net',
        'company': 'AgileWorks',
        'job_title': 'Scrum Master',
        'phone': '+1-555-0117',
    },
    {
        'first_name': 'Rachel',
        'last_name': 'Robinson',
        'email': 'rachel@sunrisemedia.co',
        'company': 'Sunrise Media',
        'job_title': 'Social Media Manager',
        'phone': '+1-555-0118',
    },
    {
        'first_name': 'Steve',
        'last_name': 'Clark',
        'email': 'steve@alphalogistics.com',
        'company': 'Alpha Logistics',
        'job_title': 'Supply Chain Director',
        'phone': '+1-555-0119',
    },
    {
        'first_name': 'Tina',
        'last_name': 'Lewis',
        'email': 'tina@cubecreative.io',
        'company': 'Cube Creative',
        'job_title': 'UX Designer',
        'phone': '+1-555-0120',
    },
]


class LeadImportService:
    """Service for importing leads from social integrations."""

    @staticmethod
    @transaction.atomic
    def import_leads(integration):
        """
        Import leads from a social integration.
        Creates a sync log and dispatches to the appropriate handler.
        """
        sync_log = LeadSyncLog.objects.create(
            integration=integration,
            status='running',
        )

        try:
            if integration.is_demo:
                LeadImportService._generate_demo_leads(integration, sync_log)
            elif integration.platform == 'facebook_lead_ads':
                LeadImportService._import_facebook_leads(integration, sync_log)
            elif integration.platform == 'linkedin_lead_gen':
                LeadImportService._import_linkedin_leads(integration, sync_log)
            else:
                sync_log.status = 'failed'
                sync_log.error_message = f'Unsupported platform: {integration.platform}'
                sync_log.completed_at = timezone.now()
                sync_log.save(update_fields=[
                    'status', 'error_message', 'completed_at', 'updated_at',
                ])
        except Exception as e:
            logger.error(f"Lead import failed for integration {integration.id}: {e}")
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            sync_log.completed_at = timezone.now()
            sync_log.save(update_fields=[
                'status', 'error_message', 'completed_at', 'updated_at',
            ])

        return sync_log

    @staticmethod
    def _generate_demo_leads(integration, sync_log):
        """Generate 5-15 random demo contacts for testing."""
        num_leads = random.randint(5, 15)
        sample_leads = random.sample(DEMO_LEADS, min(num_leads, len(DEMO_LEADS)))

        leads_created = 0
        leads_updated = 0
        leads_failed = 0

        for lead_data in sample_leads:
            try:
                contact, created = LeadImportService._map_lead_to_contact(
                    lead_data=lead_data,
                    field_mapping=integration.field_mapping,
                    organization=integration.organization,
                    default_tag=integration.default_tag,
                )
                if created:
                    leads_created += 1
                else:
                    leads_updated += 1
            except Exception as e:
                logger.warning(f"Failed to import demo lead: {e}")
                leads_failed += 1

        now = timezone.now()
        sync_log.leads_found = len(sample_leads)
        sync_log.leads_created = leads_created
        sync_log.leads_updated = leads_updated
        sync_log.leads_failed = leads_failed
        sync_log.status = 'completed'
        sync_log.completed_at = now
        sync_log.save(update_fields=[
            'leads_found', 'leads_created', 'leads_updated', 'leads_failed',
            'status', 'completed_at', 'updated_at',
        ])

        # Update integration stats
        integration.total_leads_imported += leads_created
        integration.last_synced_at = now
        integration.save(update_fields=[
            'total_leads_imported', 'last_synced_at', 'updated_at',
        ])

    @staticmethod
    def _import_facebook_leads(integration, sync_log):
        """Stub for Facebook Lead Ads API import."""
        sync_log.status = 'failed'
        sync_log.error_message = (
            'Facebook Lead Ads API not configured. Use demo mode for testing.'
        )
        sync_log.completed_at = timezone.now()
        sync_log.save(update_fields=[
            'status', 'error_message', 'completed_at', 'updated_at',
        ])

    @staticmethod
    def _import_linkedin_leads(integration, sync_log):
        """Stub for LinkedIn Lead Gen API import."""
        sync_log.status = 'failed'
        sync_log.error_message = (
            'LinkedIn Lead Gen API not configured. Use demo mode for testing.'
        )
        sync_log.completed_at = timezone.now()
        sync_log.save(update_fields=[
            'status', 'error_message', 'completed_at', 'updated_at',
        ])

    @staticmethod
    def _map_lead_to_contact(lead_data, field_mapping, organization, default_tag=None):
        """
        Map platform lead data to a Contact using the field mapping.
        Returns (contact, created) tuple.
        """
        from apps.contacts.models import Contact, ContactTag

        # Build contact fields from lead data using field mapping
        contact_fields = {}
        for platform_field, contact_field in field_mapping.items():
            if platform_field in lead_data and contact_field:
                contact_fields[contact_field] = lead_data[platform_field]

        # Ensure email is always mapped (fallback to direct key)
        email = contact_fields.pop('email', None) or lead_data.get('email')
        if not email:
            raise ValueError('Lead data must contain an email address')

        # Set source to integration
        contact_fields['source'] = 'integration'

        contact, created = Contact.objects.update_or_create(
            organization=organization,
            email=email,
            defaults=contact_fields,
        )

        # Apply default tag if set
        if default_tag:
            ContactTag.objects.get_or_create(
                contact=contact,
                tag=default_tag,
            )

        return contact, created
