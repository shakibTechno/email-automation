from django.db import migrations


def mark_existing_addresses_verified(apps, schema_editor):
    """
    Treat every account that already exists as confirmed.

    `is_email_verified` has been on the model for a long time with nothing to
    set it, so every account predating the confirmation flow reads as
    unverified. That is not a finding about those addresses — it is an artefact
    of the flag never having been written. Leaving them false means that the
    first time verification gates anything, everyone who signed up before today
    is locked out at once.

    These accounts have other evidence behind them: they were invited by
    someone who typed the address, or they signed in and used the product.
    """
    User = apps.get_model('accounts', 'User')
    User.objects.filter(is_email_verified=False).update(is_email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_user_reply_to_email'),
    ]

    operations = [
        # Deliberately irreversible in the data sense: reversing it would clear
        # the flag on accounts that have genuinely confirmed since, which is
        # worse than the state it undoes.
        migrations.RunPython(
            mark_existing_addresses_verified,
            migrations.RunPython.noop,
        ),
    ]
