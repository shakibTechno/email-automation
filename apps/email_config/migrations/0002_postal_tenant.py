"""
Postal multi-tenant sending.

Hand-written rather than generated. `makemigrations` wanted to bundle
pre-existing model/migration drift into this file — swapping SendingDomain's
named UniqueConstraint for an equivalent unique_together, and AlterFields for
help_text changes on five EmailConfiguration columns. None of that belongs to
this feature, and on SQLite the constraint swap forces a table rebuild, so this
migration carries only the Postal changes and leaves that drift for a separate
decision.
"""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_emailconfiguration"),
        ("email_config", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostalTenant",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("external_id", models.CharField(max_length=48, unique=True)),
                ("postal_tenant_id", models.CharField(blank=True, max_length=64)),
                ("api_key", models.CharField(blank=True, max_length=512)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("error", "Error"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("suspension_reason", models.TextField(blank=True)),
                (
                    "send_limit_per_hour",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text=(
                            "Postal holds mail above this and it must be released by "
                            "hand, so treat it as a circuit breaker rather than a "
                            "throttle."
                        ),
                        null=True,
                    ),
                ),
                ("ip_pool", models.CharField(blank=True, max_length=100)),
                ("sent_last_hour", models.PositiveIntegerField(default=0)),
                ("queued", models.PositiveIntegerField(default=0)),
                ("held", models.PositiveIntegerField(default=0)),
                (
                    "bounce_rate_30d",
                    models.DecimalField(decimal_places=2, default=0, max_digits=6),
                ),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
            ],
            options={
                "db_table": "postal_tenants",
            },
        ),
        migrations.AddField(
            model_name="postaltenant",
            name="organization",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="postal_tenant",
                to="accounts.organization",
            ),
        ),
        migrations.AddField(
            model_name="sendingdomain",
            name="dns_records",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="sendingdomain",
            name="sending_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="emailconfiguration",
            name="provider",
            field=models.CharField(
                choices=[
                    ("platform_default", "Platform Default (shared SMTP)"),
                    ("postal", "Postal (platform mail server)"),
                    ("smtp", "Custom SMTP"),
                    ("sendgrid", "SendGrid"),
                    ("mailgun", "Mailgun"),
                    ("ses", "Amazon SES"),
                ],
                default="platform_default",
                max_length=30,
            ),
        ),
    ]
