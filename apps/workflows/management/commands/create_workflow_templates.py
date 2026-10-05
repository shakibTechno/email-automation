"""
Management command to create system workflow templates.
"""
from django.core.management.base import BaseCommand
from apps.workflows.models import WorkflowTemplate


class Command(BaseCommand):
    help = 'Creates system workflow templates'

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'Welcome Series',
                'description': 'Send a series of welcome emails to new contacts over several days.',
                'category': 'welcome_series',
                'template_data': {
                    'nodes': [
                        {
                            'id': 'trigger-1',
                            'node_type': 'trigger_contact_created',
                            'position_x': 250,
                            'position_y': 50,
                            'config': {},
                            'label': 'New Contact',
                        },
                        {
                            'id': 'action-1',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 150,
                            'config': {},
                            'label': 'Welcome Email',
                        },
                        {
                            'id': 'action-2',
                            'node_type': 'action_wait',
                            'position_x': 250,
                            'position_y': 250,
                            'config': {'duration': 2, 'unit': 'days'},
                            'label': 'Wait 2 Days',
                        },
                        {
                            'id': 'action-3',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 350,
                            'config': {},
                            'label': 'Getting Started Guide',
                        },
                        {
                            'id': 'action-4',
                            'node_type': 'action_wait',
                            'position_x': 250,
                            'position_y': 450,
                            'config': {'duration': 3, 'unit': 'days'},
                            'label': 'Wait 3 Days',
                        },
                        {
                            'id': 'action-5',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 550,
                            'config': {},
                            'label': 'Tips & Resources',
                        },
                    ],
                    'edges': [
                        {'source_node_id': 'trigger-1', 'target_node_id': 'action-1', 'edge_type': 'default'},
                        {'source_node_id': 'action-1', 'target_node_id': 'action-2', 'edge_type': 'default'},
                        {'source_node_id': 'action-2', 'target_node_id': 'action-3', 'edge_type': 'default'},
                        {'source_node_id': 'action-3', 'target_node_id': 'action-4', 'edge_type': 'default'},
                        {'source_node_id': 'action-4', 'target_node_id': 'action-5', 'edge_type': 'default'},
                    ],
                },
            },
            {
                'name': 'Lead Nurturing',
                'description': 'Automatically nurture leads based on their engagement level.',
                'category': 'lead_nurturing',
                'template_data': {
                    'nodes': [
                        {
                            'id': 'trigger-1',
                            'node_type': 'trigger_form_submission',
                            'position_x': 250,
                            'position_y': 50,
                            'config': {},
                            'label': 'Form Submitted',
                        },
                        {
                            'id': 'action-1',
                            'node_type': 'action_add_tag',
                            'position_x': 250,
                            'position_y': 150,
                            'config': {},
                            'label': 'Tag as Lead',
                        },
                        {
                            'id': 'action-2',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 250,
                            'config': {},
                            'label': 'Introduction Email',
                        },
                        {
                            'id': 'action-3',
                            'node_type': 'action_wait',
                            'position_x': 250,
                            'position_y': 350,
                            'config': {'duration': 3, 'unit': 'days'},
                            'label': 'Wait 3 Days',
                        },
                        {
                            'id': 'condition-1',
                            'node_type': 'condition_if_else',
                            'position_x': 250,
                            'position_y': 450,
                            'config': {
                                'rules': [{'field': 'lead_score', 'operator': 'greater_than', 'value': '50'}],
                                'logic': 'all',
                            },
                            'label': 'Lead Score > 50?',
                        },
                        {
                            'id': 'action-4',
                            'node_type': 'action_send_email',
                            'position_x': 100,
                            'position_y': 550,
                            'config': {},
                            'label': 'High Value Email',
                        },
                        {
                            'id': 'action-5',
                            'node_type': 'action_send_email',
                            'position_x': 400,
                            'position_y': 550,
                            'config': {},
                            'label': 'Standard Nurture Email',
                        },
                        {
                            'id': 'goal-1',
                            'node_type': 'action_goal',
                            'position_x': 250,
                            'position_y': 650,
                            'config': {},
                            'label': 'Nurturing Complete',
                        },
                    ],
                    'edges': [
                        {'source_node_id': 'trigger-1', 'target_node_id': 'action-1', 'edge_type': 'default'},
                        {'source_node_id': 'action-1', 'target_node_id': 'action-2', 'edge_type': 'default'},
                        {'source_node_id': 'action-2', 'target_node_id': 'action-3', 'edge_type': 'default'},
                        {'source_node_id': 'action-3', 'target_node_id': 'condition-1', 'edge_type': 'default'},
                        {'source_node_id': 'condition-1', 'target_node_id': 'action-4', 'edge_type': 'true'},
                        {'source_node_id': 'condition-1', 'target_node_id': 'action-5', 'edge_type': 'false'},
                        {'source_node_id': 'action-4', 'target_node_id': 'goal-1', 'edge_type': 'default'},
                        {'source_node_id': 'action-5', 'target_node_id': 'goal-1', 'edge_type': 'default'},
                    ],
                },
            },
            {
                'name': 'Re-engagement Campaign',
                'description': 'Win back inactive contacts with targeted emails.',
                'category': 're_engagement',
                'template_data': {
                    'nodes': [
                        {
                            'id': 'trigger-1',
                            'node_type': 'trigger_tag_added',
                            'position_x': 250,
                            'position_y': 50,
                            'config': {},
                            'label': 'Tagged as Inactive',
                        },
                        {
                            'id': 'action-1',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 150,
                            'config': {},
                            'label': 'We Miss You Email',
                        },
                        {
                            'id': 'action-2',
                            'node_type': 'action_wait',
                            'position_x': 250,
                            'position_y': 250,
                            'config': {'duration': 5, 'unit': 'days'},
                            'label': 'Wait 5 Days',
                        },
                        {
                            'id': 'action-3',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 350,
                            'config': {},
                            'label': 'Special Offer Email',
                        },
                        {
                            'id': 'action-4',
                            'node_type': 'action_wait',
                            'position_x': 250,
                            'position_y': 450,
                            'config': {'duration': 7, 'unit': 'days'},
                            'label': 'Wait 7 Days',
                        },
                        {
                            'id': 'action-5',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 550,
                            'config': {},
                            'label': 'Last Chance Email',
                        },
                    ],
                    'edges': [
                        {'source_node_id': 'trigger-1', 'target_node_id': 'action-1', 'edge_type': 'default'},
                        {'source_node_id': 'action-1', 'target_node_id': 'action-2', 'edge_type': 'default'},
                        {'source_node_id': 'action-2', 'target_node_id': 'action-3', 'edge_type': 'default'},
                        {'source_node_id': 'action-3', 'target_node_id': 'action-4', 'edge_type': 'default'},
                        {'source_node_id': 'action-4', 'target_node_id': 'action-5', 'edge_type': 'default'},
                    ],
                },
            },
            {
                'name': 'Birthday Automation',
                'description': 'Send birthday wishes on or before a contacts birthday.',
                'category': 'promotional',
                'template_data': {
                    'nodes': [
                        {
                            'id': 'trigger-1',
                            'node_type': 'trigger_date_field',
                            'position_x': 250,
                            'position_y': 50,
                            'config': {'field_name': 'birthday', 'offset_days': 0, 'time': '09:00'},
                            'label': 'Birthday Today',
                        },
                        {
                            'id': 'action-1',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 150,
                            'config': {},
                            'label': 'Birthday Email',
                        },
                        {
                            'id': 'action-2',
                            'node_type': 'action_update_contact',
                            'position_x': 250,
                            'position_y': 250,
                            'config': {'field': 'lead_score', 'operation': 'increment', 'value': 5},
                            'label': 'Increase Lead Score',
                        },
                    ],
                    'edges': [
                        {'source_node_id': 'trigger-1', 'target_node_id': 'action-1', 'edge_type': 'default'},
                        {'source_node_id': 'action-1', 'target_node_id': 'action-2', 'edge_type': 'default'},
                    ],
                },
            },
            {
                'name': 'Onboarding Sequence',
                'description': 'Guide new users through your product features over time.',
                'category': 'onboarding',
                'template_data': {
                    'nodes': [
                        {
                            'id': 'trigger-1',
                            'node_type': 'trigger_tag_added',
                            'position_x': 250,
                            'position_y': 50,
                            'config': {},
                            'label': 'Tagged as New User',
                        },
                        {
                            'id': 'action-1',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 150,
                            'config': {},
                            'label': 'Day 1: Getting Started',
                        },
                        {
                            'id': 'action-2',
                            'node_type': 'action_wait',
                            'position_x': 250,
                            'position_y': 250,
                            'config': {'duration': 1, 'unit': 'days'},
                            'label': 'Wait 1 Day',
                        },
                        {
                            'id': 'action-3',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 350,
                            'config': {},
                            'label': 'Day 2: Core Features',
                        },
                        {
                            'id': 'action-4',
                            'node_type': 'action_wait',
                            'position_x': 250,
                            'position_y': 450,
                            'config': {'duration': 2, 'unit': 'days'},
                            'label': 'Wait 2 Days',
                        },
                        {
                            'id': 'action-5',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 550,
                            'config': {},
                            'label': 'Day 4: Pro Tips',
                        },
                        {
                            'id': 'action-6',
                            'node_type': 'action_wait',
                            'position_x': 250,
                            'position_y': 650,
                            'config': {'duration': 3, 'unit': 'days'},
                            'label': 'Wait 3 Days',
                        },
                        {
                            'id': 'action-7',
                            'node_type': 'action_send_email',
                            'position_x': 250,
                            'position_y': 750,
                            'config': {},
                            'label': 'Day 7: Success Stories',
                        },
                        {
                            'id': 'action-8',
                            'node_type': 'action_remove_tag',
                            'position_x': 250,
                            'position_y': 850,
                            'config': {},
                            'label': 'Remove New User Tag',
                        },
                        {
                            'id': 'goal-1',
                            'node_type': 'action_goal',
                            'position_x': 250,
                            'position_y': 950,
                            'config': {},
                            'label': 'Onboarding Complete',
                        },
                    ],
                    'edges': [
                        {'source_node_id': 'trigger-1', 'target_node_id': 'action-1', 'edge_type': 'default'},
                        {'source_node_id': 'action-1', 'target_node_id': 'action-2', 'edge_type': 'default'},
                        {'source_node_id': 'action-2', 'target_node_id': 'action-3', 'edge_type': 'default'},
                        {'source_node_id': 'action-3', 'target_node_id': 'action-4', 'edge_type': 'default'},
                        {'source_node_id': 'action-4', 'target_node_id': 'action-5', 'edge_type': 'default'},
                        {'source_node_id': 'action-5', 'target_node_id': 'action-6', 'edge_type': 'default'},
                        {'source_node_id': 'action-6', 'target_node_id': 'action-7', 'edge_type': 'default'},
                        {'source_node_id': 'action-7', 'target_node_id': 'action-8', 'edge_type': 'default'},
                        {'source_node_id': 'action-8', 'target_node_id': 'goal-1', 'edge_type': 'default'},
                    ],
                },
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = WorkflowTemplate.objects.update_or_create(
                name=template_data['name'],
                is_system=True,
                defaults={
                    'description': template_data['description'],
                    'category': template_data['category'],
                    'template_data': template_data['template_data'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} and updated {updated_count} workflow templates'
            )
        )
