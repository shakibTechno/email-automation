from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('contacts', '0001_initial'),
        ('templates', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailSequence',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('paused', 'Paused'), ('archived', 'Archived')], default='draft', max_length=20)),
                ('sender_name', models.CharField(blank=True, max_length=255)),
                ('sender_email', models.EmailField(blank=True, max_length=254)),
                ('reply_to_email', models.EmailField(blank=True, max_length=254)),
                ('allow_reenrollment', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_sequences', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sequences', to='accounts.organization')),
            ],
            options={
                'db_table': 'sequences',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SequenceStep',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('position', models.PositiveIntegerField(default=0)),
                ('subject', models.CharField(max_length=500)),
                ('delay_days', models.PositiveIntegerField(default=0)),
                ('delay_hours', models.PositiveIntegerField(default=0)),
                ('sequence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='sequences.emailsequence')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sequence_steps', to='templates.emailtemplate')),
            ],
            options={
                'db_table': 'sequence_steps',
                'ordering': ['position'],
            },
        ),
        migrations.CreateModel(
            name='SequenceEnrollment',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('active', 'Active'), ('completed', 'Completed'), ('unsubscribed', 'Unsubscribed'), ('paused', 'Paused'), ('cancelled', 'Cancelled')], default='active', max_length=20)),
                ('current_step_position', models.PositiveIntegerField(default=0)),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('next_send_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('contact', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sequence_enrollments', to='contacts.contact')),
                ('enrolled_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sequence_enrollments_made', to=settings.AUTH_USER_MODEL)),
                ('sequence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to='sequences.emailsequence')),
            ],
            options={
                'db_table': 'sequence_enrollments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SequenceStepExecution',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'), ('skipped', 'Skipped')], default='pending', max_length=20)),
                ('scheduled_at', models.DateTimeField()),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('opened_at', models.DateTimeField(blank=True, null=True)),
                ('clicked_at', models.DateTimeField(blank=True, null=True)),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='step_executions', to='sequences.sequenceenrollment')),
                ('step', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='sequences.sequencestep')),
            ],
            options={
                'db_table': 'sequence_step_executions',
                'ordering': ['scheduled_at'],
            },
        ),
        migrations.AddIndex(
            model_name='emailsequence',
            index=models.Index(fields=['organization', 'status'], name='seq_org_status_idx'),
        ),
        migrations.AddIndex(
            model_name='sequencestep',
            index=models.Index(fields=['sequence', 'position'], name='step_seq_pos_idx'),
        ),
        migrations.AddConstraint(
            model_name='sequencestep',
            constraint=models.UniqueConstraint(fields=['sequence', 'position'], name='unique_seq_step_position'),
        ),
        migrations.AddIndex(
            model_name='sequenceenrollment',
            index=models.Index(fields=['sequence', 'status'], name='enroll_seq_status_idx'),
        ),
        migrations.AddIndex(
            model_name='sequenceenrollment',
            index=models.Index(fields=['contact'], name='enroll_contact_idx'),
        ),
        migrations.AddIndex(
            model_name='sequenceenrollment',
            index=models.Index(fields=['next_send_at', 'status'], name='enroll_next_send_idx'),
        ),
        migrations.AddConstraint(
            model_name='sequenceenrollment',
            constraint=models.UniqueConstraint(fields=['sequence', 'contact'], name='unique_seq_contact'),
        ),
        migrations.AddIndex(
            model_name='sequencestepexecution',
            index=models.Index(fields=['enrollment'], name='stepexec_enroll_idx'),
        ),
        migrations.AddIndex(
            model_name='sequencestepexecution',
            index=models.Index(fields=['scheduled_at', 'status'], name='stepexec_sched_idx'),
        ),
        migrations.AddConstraint(
            model_name='sequencestepexecution',
            constraint=models.UniqueConstraint(fields=['enrollment', 'step'], name='unique_enroll_step'),
        ),
    ]
