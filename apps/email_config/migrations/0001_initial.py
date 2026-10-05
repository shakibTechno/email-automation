from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailConfiguration',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('from_name', models.CharField(blank=True, max_length=255)),
                ('from_email', models.EmailField(blank=True, max_length=254)),
                ('reply_to_email', models.EmailField(blank=True, max_length=254)),
                ('provider', models.CharField(
                    choices=[
                        ('platform_default', 'Platform Default (shared SMTP)'),
                        ('smtp', 'Custom SMTP'),
                        ('sendgrid', 'SendGrid'),
                        ('mailgun', 'Mailgun'),
                        ('ses', 'Amazon SES'),
                    ],
                    default='platform_default', max_length=30,
                )),
                ('smtp_host', models.CharField(blank=True, max_length=255)),
                ('smtp_port', models.PositiveIntegerField(default=587)),
                ('smtp_username', models.CharField(blank=True, max_length=255)),
                ('smtp_password', models.CharField(blank=True, max_length=512)),
                ('smtp_use_tls', models.BooleanField(default=True)),
                ('smtp_use_ssl', models.BooleanField(default=False)),
                ('api_key', models.CharField(blank=True, max_length=512)),
                ('provider_domain', models.CharField(blank=True, max_length=255)),
                ('provider_region', models.CharField(blank=True, default='us-east-1', max_length=50)),
                ('physical_address', models.TextField(blank=True)),
                ('email_footer_text', models.TextField(blank=True)),
                ('unsubscribe_redirect_url', models.URLField(blank=True)),
                ('daily_send_limit', models.PositiveIntegerField(default=0)),
                ('hourly_send_limit', models.PositiveIntegerField(default=0)),
                ('bounce_threshold_pct', models.DecimalField(decimal_places=2, default='5.00', max_digits=5)),
                ('complaint_threshold_pct', models.DecimalField(decimal_places=2, default='0.10', max_digits=5)),
                ('sending_paused_due_to_threshold', models.BooleanField(default=False)),
                ('organization', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='email_config',
                    to='accounts.organization',
                )),
            ],
            options={'db_table': 'org_email_configs'},
        ),
        migrations.CreateModel(
            name='SendingDomain',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('domain', models.CharField(max_length=255)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('verified', 'Verified'), ('failed', 'Failed')],
                    default='pending', max_length=20,
                )),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('spf_record', models.TextField(blank=True)),
                ('dkim_selector', models.CharField(blank=True, max_length=64)),
                ('dkim_public_key', models.TextField(blank=True)),
                ('dkim_record_name', models.CharField(blank=True, max_length=255)),
                ('dkim_record_value', models.TextField(blank=True)),
                ('last_check_at', models.DateTimeField(blank=True, null=True)),
                ('last_check_error', models.TextField(blank=True)),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sending_domains',
                    to='accounts.organization',
                )),
            ],
            options={'db_table': 'sending_domains', 'ordering': ['-created_at']},
        ),
        migrations.AddConstraint(
            model_name='sendingdomain',
            constraint=models.UniqueConstraint(fields=['organization', 'domain'], name='unique_org_domain'),
        ),
    ]
