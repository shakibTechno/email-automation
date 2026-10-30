import uuid

from django.db import migrations, models


def give_each_organization_a_key(apps, schema_editor):
    """
    A distinct key per organization.

    Written by hand rather than left to `default=uuid.uuid4`, because a default
    is evaluated once for an AddField and every existing row would receive the
    same value — which a unique constraint then refuses, and which would have
    meant one tenant's popups served to another's website had it not.
    """
    Organization = apps.get_model('accounts', 'Organization')
    for organization in Organization.objects.all().iterator():
        Organization.objects.filter(pk=organization.pk).update(
            tracking_key=uuid.uuid4()
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_backfill_email_verified'),
    ]

    # Three steps on purpose: a unique column cannot be added to a populated
    # table in one, because every row would arrive holding the same default.
    operations = [
        migrations.AddField(
            model_name='organization',
            name='tracking_key',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(
            give_each_organization_a_key, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='organization',
            name='tracking_key',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
