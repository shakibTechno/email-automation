"""
Record why sending was paused, and when.

`sending_paused_due_to_threshold` is now set by two things — the deliverability
guardrails automatically, and the landlord console manually. One flag with a
reason beats two flags that drift apart.

Hand-written to avoid bundling the pre-existing SendingDomain constraint drift
that `makemigrations` wants to materialise in this app.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('email_config', '0002_postal_tenant'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailconfiguration',
            name='sending_pause_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='emailconfiguration',
            name='sending_paused_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
