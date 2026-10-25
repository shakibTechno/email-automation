"""
Add the 'business' tier to Organization.plan.

billing.Plan has had five tiers since the initial data migration, and
BillingService writes `organization.plan = new_plan.plan_type` on every
upgrade — so 'business' was already being stored in a column whose choices did
not list it. Django validates choices only in full_clean(), which save() skips,
so it persisted silently while every hand-written tier tuple excluded it.

Choices are not enforced at the database level, so this alters state and the
field's validation only; no data changes.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_emailconfiguration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='plan',
            field=models.CharField(
                choices=[
                    ('free', 'Free'),
                    ('starter', 'Starter'),
                    ('professional', 'Professional'),
                    ('business', 'Business'),
                    ('enterprise', 'Enterprise'),
                ],
                default='free',
                max_length=20,
            ),
        ),
    ]
