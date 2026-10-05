from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0003_campaign_status_archived'),
        ('templates', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaignrecipient',
            name='ab_variant',
            field=models.CharField(blank=True, db_index=True, max_length=10, null=True),
        ),
        migrations.CreateModel(
            name='ABTest',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('test_type', models.CharField(
                    choices=[('subject', 'Subject Line'), ('sender_name', 'Sender Name'), ('content', 'Email Content')],
                    max_length=20,
                )),
                ('test_percentage', models.PositiveIntegerField(default=20)),
                ('winner_criteria', models.CharField(
                    choices=[('open_rate', 'Open Rate'), ('click_rate', 'Click Rate')],
                    default='open_rate', max_length=20,
                )),
                ('winner_selection', models.CharField(
                    choices=[('auto', 'Automatic'), ('manual', 'Manual')],
                    default='auto', max_length=20,
                )),
                ('test_duration_hours', models.PositiveIntegerField(default=4)),
                ('winner_variant', models.CharField(blank=True, max_length=1, null=True)),
                ('status', models.CharField(
                    choices=[('draft', 'Draft'), ('testing', 'Testing'), ('winner_declared', 'Winner Declared'), ('completed', 'Completed')],
                    default='draft', max_length=20,
                )),
                ('winner_sent_at', models.DateTimeField(blank=True, null=True)),
                ('campaign', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ab_test',
                    to='campaigns.campaign',
                )),
            ],
            options={'db_table': 'campaign_ab_tests'},
        ),
        migrations.CreateModel(
            name='ABTestVariant',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('variant', models.CharField(choices=[('a', 'Variant A'), ('b', 'Variant B')], max_length=1)),
                ('subject', models.CharField(blank=True, max_length=500)),
                ('sender_name', models.CharField(blank=True, max_length=200)),
                ('recipient_count', models.PositiveIntegerField(default=0)),
                ('sent_count', models.PositiveIntegerField(default=0)),
                ('open_count', models.PositiveIntegerField(default=0)),
                ('click_count', models.PositiveIntegerField(default=0)),
                ('ab_test', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='variants',
                    to='campaigns.abtest',
                )),
                ('template', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ab_variants',
                    to='templates.emailtemplate',
                )),
            ],
            options={
                'db_table': 'campaign_ab_test_variants',
                'unique_together': {('ab_test', 'variant')},
            },
        ),
    ]
