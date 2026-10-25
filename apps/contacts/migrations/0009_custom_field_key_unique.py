"""
Make the custom field key unique per organization.

Separate from 0006, which adds the column, because it has to run *after* 0007
has derived a key for every existing definition. Applied together with the
column, this constraint would be checked while every pre-existing row still
held a blank key — so any organization with two custom fields could not migrate
at all. Found by a test whose fixture created two definitions.

The key is what values are stored under, so two definitions sharing one would
make the stored data ambiguous; that is why it is constrained rather than left
to the application.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0008_custom_fields_gin'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='customfield',
            unique_together={('organization', 'key'), ('organization', 'name')},
        ),
        migrations.AddIndex(
            model_name='customfield',
            index=models.Index(
                fields=['organization', 'key'],
                name='custom_fiel_organiz_c0c613_idx',
            ),
        ),
    ]
