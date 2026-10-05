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
        """Create a notification for every admin/owner in the organization."""
        from apps.accounts.models import OrganizationMember
        from .models import Notification

        admin_roles = ('owner', 'admin')
        members = OrganizationMember.objects.filter(
            organization=organization,
            role__in=admin_roles,
        ).select_related('user')

        notifications = [
            Notification(
                organization=organization,
                user=member.user,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data or {},
            )
            for member in members
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
