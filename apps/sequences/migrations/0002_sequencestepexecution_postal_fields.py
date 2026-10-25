"""
Delivery tracking fields on sequence step executions.

Hand-written: `makemigrations` wanted to bundle pre-existing drift into this
file — dropping three named UniqueConstraints for equivalent unique_togethers
and renaming seven indexes to Django's auto-generated names. That churn is
unrelated to this feature and rebuilds tables on SQLite, so only the new
columns are here.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sequences", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sequencestepexecution",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sequencestepexecution",
            name="bounced_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sequencestepexecution",
            name="postal_id",
            field=models.BigIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="sequencestepexecution",
            name="postal_token",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
    ]
