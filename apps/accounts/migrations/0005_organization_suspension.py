"""
Account-level suspension fields on Organization.

`is_active` already existed but was read in exactly one place in the codebase,
so suspending a tenant did nothing. These record who/why/when alongside it, now
that login, the API permission layer and the send path all honour it.

Hand-written rather than generated: `makemigrations` would bundle the
pre-existing index and constraint drift in other apps, and running it inside the
container writes to the baked image copy rather than the repository.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_organization_plan'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='suspended_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='organization',
            name='suspension_reason',
            field=models.TextField(blank=True),
        ),
    ]
