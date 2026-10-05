import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('contacts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScoringRule',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('rule_type', models.CharField(
                    choices=[('demographic', 'Demographic'), ('behavioral', 'Behavioral')],
                    max_length=20,
                )),
                ('points', models.IntegerField()),
                ('is_active', models.BooleanField(default=True)),
                ('priority', models.PositiveIntegerField(default=0)),
                ('condition', models.JSONField(blank=True, default=dict)),
                ('event_type', models.CharField(
                    blank=True,
                    choices=[
                        ('email_opened', 'Email Opened'),
                        ('email_clicked', 'Email Clicked'),
                        ('form_submitted', 'Form Submitted'),
                        ('tag_added', 'Tag Added'),
                        ('tag_removed', 'Tag Removed'),
                        ('workflow_completed', 'Workflow Completed'),
                        ('unsubscribed', 'Unsubscribed'),
                        ('bounced', 'Bounced'),
                    ],
                    max_length=30,
                )),
                ('event_filter', models.JSONField(blank=True, default=dict)),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='scoring_rules',
                    to='accounts.organization',
                )),
            ],
            options={
                'db_table': 'lead_scoring_rules',
                'ordering': ['priority', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ScoreThreshold',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('label', models.CharField(max_length=50)),
                ('min_score', models.IntegerField()),
                ('color', models.CharField(default='blue', max_length=20)),
                ('engagement_level', models.CharField(
                    choices=[
                        ('high', 'High'), ('medium', 'Medium'),
                        ('low', 'Low'), ('none', 'None'),
                    ],
                    default='none',
                    max_length=10,
                )),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='score_thresholds',
                    to='accounts.organization',
                )),
            ],
            options={
                'db_table': 'lead_score_thresholds',
                'ordering': ['min_score'],
            },
        ),
        migrations.CreateModel(
            name='ScoreHistory',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('reason', models.CharField(
                    choices=[
                        ('rule', 'Rule Triggered'),
                        ('manual', 'Manual Adjustment'),
                        ('recalculation', 'Recalculation'),
                    ],
                    max_length=20,
                )),
                ('points_delta', models.IntegerField()),
                ('score_before', models.IntegerField()),
                ('score_after', models.IntegerField()),
                ('note', models.CharField(blank=True, max_length=255)),
                ('contact', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='score_history',
                    to='contacts.contact',
                )),
                ('rule', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='history_entries',
                    to='lead_scoring.scoringrule',
                )),
            ],
            options={
                'db_table': 'lead_score_history',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='scoringrule',
            index=models.Index(fields=['organization', 'is_active'], name='ls_rule_org_active_idx'),
        ),
        migrations.AddIndex(
            model_name='scoringrule',
            index=models.Index(fields=['organization', 'rule_type'], name='ls_rule_org_type_idx'),
        ),
        migrations.AddIndex(
            model_name='scoringrule',
            index=models.Index(fields=['organization', 'event_type'], name='ls_rule_org_event_idx'),
        ),
        migrations.AddIndex(
            model_name='scorethreshold',
            index=models.Index(fields=['organization', 'min_score'], name='ls_threshold_org_score_idx'),
        ),
        migrations.AddIndex(
            model_name='scorehistory',
            index=models.Index(fields=['contact', '-created_at'], name='ls_history_contact_time_idx'),
        ),
        migrations.AddIndex(
            model_name='scorehistory',
            index=models.Index(fields=['contact', 'reason'], name='ls_history_contact_reason_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='scorethreshold',
            unique_together={('organization', 'label')},
        ),
    ]
