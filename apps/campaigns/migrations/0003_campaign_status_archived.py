from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0002_add_email_tracking'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaign',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('scheduled', 'Scheduled'),
                    ('sending', 'Sending'),
                    ('sent', 'Sent'),
                    ('paused', 'Paused'),
                    ('cancelled', 'Cancelled'),
                    ('archived', 'Archived'),
                ],
                default='draft',
                max_length=20,
            ),
        ),
    ]
