"""
Derive `status` for contacts that existed before the column did.

The schema migration gives every row the `active` default, which is wrong for
every contact who had already unsubscribed or bounced — and subscription state
is the one thing here with legal weight. This computes it from the flags that
have always recorded it, in the same order as `Contact.derived_status`:
complaint beats bounce beats unsubscribe.

Written as bulk UPDATEs rather than a loop over model instances. A row-by-row
save() would be slow on a large table, and `Contact.save()` recomputes `status`
anyway — which would work, but makes the migration depend on model code that
may have moved on by the time anyone runs it on an old database.
"""
from django.db import migrations


def backfill_status(apps, schema_editor):
    Contact = apps.get_model('contacts', 'Contact')

    # Most specific first; each later UPDATE excludes the rows already claimed,
    # so the order of precedence is explicit rather than relying on overwrite
    # order.
    Contact.objects.filter(complained_at__isnull=False).update(status='complained')
    Contact.objects.filter(
        complained_at__isnull=True, bounced_at__isnull=False,
    ).update(status='bounced')
    Contact.objects.filter(
        complained_at__isnull=True, bounced_at__isnull=True, is_subscribed=False,
    ).update(status='unsubscribed')
    Contact.objects.filter(
        complained_at__isnull=True, bounced_at__isnull=True, is_subscribed=True,
    ).update(status='active')


def noop(apps, schema_editor):
    """
    Nothing to undo.

    `status` is derived, so reversing this migration loses no information the
    flags do not still hold; the column itself goes with the schema migration.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0004_contact_standard_fields'),
    ]

    operations = [
        migrations.RunPython(backfill_status, noop),
    ]
