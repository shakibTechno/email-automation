"""Records the four landlord suspension actions in the activity log choices.

Choices only — no column change. Written out so the next `makemigrations`
does not fold this into an unrelated migration.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_organization_suspension"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activitylog",
            name="action",
            field=models.CharField(
                choices=[
                    ("member_invited", "Member Invited"),
                    ("member_joined", "Member Joined"),
                    ("member_removed", "Member Removed"),
                    ("role_changed", "Role Changed"),
                    ("invitation_cancelled", "Invitation Cancelled"),
                    ("invitation_resent", "Invitation Resent"),
                    ("ownership_transferred", "Ownership Transferred"),
                    ("org_settings_updated", "Organization Settings Updated"),
                    ("sending_suspended", "Sending Suspended by Platform"),
                    ("sending_resumed", "Sending Resumed by Platform"),
                    ("account_suspended", "Account Suspended by Platform"),
                    ("account_restored", "Account Restored by Platform"),
                ],
                max_length=50,
            ),
        ),
    ]
