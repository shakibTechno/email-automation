"""
Re-entry, entry gating, quiet hours, and the node types to go with them.

`webhook_token` is added in three steps on purpose: a unique UUID column on a
populated table makes `makemigrations` stop and ask for a default
interactively, and the answer it wants is "one value for every row", which a
unique column cannot take.

Existing workflows are set to `once` — exactly what they did before this
migration, where any execution row at all barred a contact for good. New
workflows get the model default, `one_at_a_time`, which is what people expect.
Nobody's live workflow changes behaviour on deploy; they can opt in per
workflow.
"""
import uuid
from datetime import time

import django.db.models.deletion
from django.db import migrations, models

from apps.workflows import catalog


def mint_tokens(apps, schema_editor):
    Workflow = apps.get_model('workflows', 'Workflow')
    for pk in Workflow.objects.filter(webhook_token__isnull=True).values_list(
        'id', flat=True,
    ):
        Workflow.objects.filter(pk=pk).update(webhook_token=uuid.uuid4())


def keep_existing_behaviour(apps, schema_editor):
    """Existing flows stay once-per-contact-ever, as they are today."""
    Workflow = apps.get_model('workflows', 'Workflow')
    Workflow.objects.all().update(reentry='once')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('segments', '0001_initial'),
        ('workflows', '0003_popup_triggers'),
    ]

    operations = [
        # ── re-entry ────────────────────────────────────────────────────────
        migrations.AddField(
            model_name='workflow',
            name='reentry',
            field=models.CharField(
                choices=[
                    ('once', 'Once ever'),
                    ('one_at_a_time', 'Again, but never twice at the same time'),
                    ('always', 'Every time the trigger fires'),
                ],
                default='one_at_a_time', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='workflow',
            name='reentry_cooldown_days',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(keep_existing_behaviour, noop),

        # ── entry gate ──────────────────────────────────────────────────────
        migrations.AddField(
            model_name='workflow',
            name='entry_segment',
            field=models.ForeignKey(
                blank=True,
                help_text='Only contacts matching this segment may enter.',
                null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='gated_workflows', to='segments.segment',
            ),
        ),

        # ── quiet hours ─────────────────────────────────────────────────────
        migrations.AddField(
            model_name='workflow',
            name='respect_quiet_hours',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='workflow',
            name='send_window_start',
            field=models.TimeField(default=time(9, 0)),
        ),
        migrations.AddField(
            model_name='workflow',
            name='send_window_end',
            field=models.TimeField(default=time(18, 0)),
        ),
        migrations.AddField(
            model_name='workflow',
            name='send_weekdays',
            field=models.JSONField(blank=True, default=list),
        ),

        # ── goal as an exit ─────────────────────────────────────────────────
        migrations.AddField(
            model_name='workflow',
            name='exit_on_goal',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='workflow',
            name='goal_rules',
            field=models.JSONField(blank=True, default=dict),
        ),

        # ── inbound webhook token, in three steps ───────────────────────────
        migrations.AddField(
            model_name='workflow',
            name='webhook_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(mint_tokens, noop),
        migrations.AlterField(
            model_name='workflow',
            name='webhook_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),

        # ── wait-until deadline ─────────────────────────────────────────────
        migrations.AddField(
            model_name='workflowexecution',
            name='wait_deadline',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # ── the catalogue's node types, and a branch per logic node ─────────
        migrations.AlterField(
            model_name='workflownode',
            name='node_type',
            field=models.CharField(choices=catalog.NODE_TYPE_CHOICES, max_length=50),
        ),
        migrations.AlterField(
            model_name='workflowedge',
            name='edge_type',
            field=models.CharField(
                choices=[
                    ('default', 'Default'), ('true', 'True Branch'),
                    ('false', 'False Branch'), ('a', 'Split A'), ('b', 'Split B'),
                    ('met', 'Condition Met'), ('timeout', 'Timed Out'),
                    ('fallback', 'Fallback'), ('named', 'Named Branch'),
                ],
                default='default', max_length=20,
            ),
        ),
    ]
