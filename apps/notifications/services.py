"""
Service layer for the Notifications app.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationService:
    """Create and manage in-app notifications."""

    @staticmethod
    def notify_org_admins(organization, notification_type, title, message, data=None):
        """
        Create a notification for every admin/owner in the organization.

        Queries User directly. This previously imported a non-existent
        `OrganizationMember` model, so every call raised ImportError — and
        because each caller wraps this in a bare `except`, no admin
        notification in the application had ever been delivered. Membership is
        a `User.organization` FK plus a `role`; there is no join model.
        """
        from apps.accounts.models import User
        from .models import Notification

        admins = User.objects.filter(
            organization=organization,
            role__in=('owner', 'admin'),
            is_active=True,
        )

        notifications = [
            Notification(
                organization=organization,
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data or {},
            )
            for user in admins
        ]
        if notifications:
            Notification.objects.bulk_create(notifications)
        return len(notifications)

    @staticmethod
    def notify_user(user, notification_type, title, message, data=None):
        """Create a notification for a specific user."""
        from .models import Notification

        return Notification.objects.create(
            organization=user.organization,
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
        )

    @staticmethod
    def mark_read(notification_id, user):
        """Mark a single notification as read."""
        from .models import Notification

        updated = Notification.objects.filter(
            id=notification_id, user=user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return updated > 0

    @staticmethod
    def mark_all_read(user):
        """Mark all unread notifications as read for a user."""
        from .models import Notification

        return Notification.objects.filter(
            user=user, is_read=False
        ).update(is_read=True, read_at=timezone.now())

    @staticmethod
    def get_unread_count(user):
        from .models import Notification

        return Notification.objects.filter(user=user, is_read=False).count()
