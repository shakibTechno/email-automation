"""
Give every existing custom field a key, and move the stored values onto it.

`key` is new; before it, `name` was both the label and — by convention, since
nothing enforced it — the JSON key under which values were stored in
`Contact.custom_fields`. Backfilling `key = slugify(name)` without touching the
data would therefore orphan every value a customer has: the definition would
say `industry_type` while the contact held `"Industry Type"`.

So this does both halves. The keys are derived first, then each contact's JSON
is rewritten to move a value from the old name-shaped key to the new one.

Keys that match no definition are left exactly as they are. The old code
validated nothing, so a contact may hold keys that were never declared —
inventing definitions for them here would be guessing, and deleting them would
be destroying data. They stay, and the first write that includes them now
reports that they are not declared.
"""
from django.db import migrations
from django.utils.text import slugify


def derive_keys(apps, schema_editor):
    CustomField = apps.get_model('contacts', 'CustomField')
    Contact = apps.get_model('contacts', 'Contact')

    # organization -> {old JSON key: new key}
    renames_by_org = {}

    for organization_id in (
        CustomField.objects.values_list('organization_id', flat=True).distinct()
    ):
        taken = set()
        renames = {}

        for definition in CustomField.objects.filter(
            organization_id=organization_id
        ).order_by('created_at', 'name'):
            if definition.key:
                taken.add(definition.key)
                continue

            base = slugify(definition.name).replace('-', '_')[:90] or 'field'
            key = base
            counter = 1
            while key in taken:
                key = f'{base}_{counter}'
                counter += 1
            taken.add(key)

            definition.key = key
            definition.save(update_fields=['key'])

            if definition.name != key:
                renames[definition.name] = key

        if renames:
            renames_by_org[organization_id] = renames

    for organization_id, renames in renames_by_org.items():
        # Only contacts that actually hold custom values, and only those whose
        # keys need moving — this runs on every deployment, most of which have
        # no custom fields at all.
        contacts = Contact.objects.filter(
            organization_id=organization_id,
        ).exclude(custom_fields={}).only('id', 'custom_fields')

        to_update = []
        for contact in contacts.iterator(chunk_size=500):
            values = contact.custom_fields or {}
            if not any(old in values for old in renames):
                continue
            moved = {}
            for key, value in values.items():
                # A value already under the new key wins: it is the more
                # recent of the two and overwriting it would be a regression.
                new_key = renames.get(key, key)
                if new_key in values and new_key != key:
                    moved[key] = value
                else:
                    moved[new_key] = value
            contact.custom_fields = moved
            to_update.append(contact)

            if len(to_update) >= 500:
                Contact.objects.bulk_update(to_update, ['custom_fields'])
                to_update = []

        if to_update:
            Contact.objects.bulk_update(to_update, ['custom_fields'])


def noop(apps, schema_editor):
    """
    Not reversed.

    Moving the values back would need the old labels, which the forward
    direction does not destroy but also does not record anywhere this could
    read. Reversing the schema drops `key`; the labels in `name` are untouched
    either way, so nothing is lost by declining to guess.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0006_custom_field_key'),
    ]

    operations = [
        migrations.RunPython(derive_keys, noop),
    ]
