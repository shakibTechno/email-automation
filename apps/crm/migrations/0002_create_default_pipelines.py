"""
Data migration to create default pipeline for each existing organization.
"""
from django.db import migrations


DEFAULT_STAGES = [
    {'name': 'Qualification', 'position': 0, 'stage_type': 'open', 'default_probability': 10, 'color': '#6366f1'},
    {'name': 'Proposal', 'position': 1, 'stage_type': 'open', 'default_probability': 30, 'color': '#8b5cf6'},
    {'name': 'Negotiation', 'position': 2, 'stage_type': 'open', 'default_probability': 60, 'color': '#a855f7'},
    {'name': 'Closed Won', 'position': 3, 'stage_type': 'won', 'default_probability': 100, 'color': '#22c55e'},
    {'name': 'Closed Lost', 'position': 4, 'stage_type': 'lost', 'default_probability': 0, 'color': '#ef4444'},
]


def create_default_pipelines(apps, schema_editor):
    Organization = apps.get_model('accounts', 'Organization')
    Pipeline = apps.get_model('crm', 'Pipeline')
    Stage = apps.get_model('crm', 'Stage')

    for org in Organization.objects.all():
        # Skip if already has a pipeline
        if Pipeline.objects.filter(organization=org).exists():
            continue

        pipeline = Pipeline.objects.create(
            organization=org,
            name='Sales Pipeline',
            description='Default sales pipeline',
            is_default=True,
        )

        for stage_data in DEFAULT_STAGES:
            Stage.objects.create(pipeline=pipeline, **stage_data)


def reverse_default_pipelines(apps, schema_editor):
    Pipeline = apps.get_model('crm', 'Pipeline')
    Pipeline.objects.filter(name='Sales Pipeline', is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_pipelines, reverse_default_pipelines),
    ]
