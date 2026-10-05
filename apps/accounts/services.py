"""
Services for team management and activity logging.
"""
import secrets
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .models import TeamInvitation, ActivityLog, Organization

logger = logging.getLogger(__name__)
User = get_user_model()


class ActivityLogService:
    """Service for logging team management activities."""

    @staticmethod
    def log(organization, user, action, target_email='', details=None):
        return ActivityLog.objects.create(
            organization=organization,
            user=user,
            action=action,
            target_email=target_email,
            details=details or {},
        )

    @staticmethod
    def get_recent(organization, limit=50):
        return ActivityLog.objects.filter(
            organization=organization
        ).select_related('user')[:limit]


class TeamService:
    """Service for team management operations."""

    @staticmethod
    def list_members(organization):
        role_order = {'owner': 0, 'admin': 1, 'member': 2, 'viewer': 3}
        members = User.objects.filter(
            organization=organization,
            is_active=True,
            deleted_at__isnull=True,
        ).order_by('first_name', 'last_name')

        return sorted(members, key=lambda u: role_order.get(u.role, 99))

    @staticmethod
    def invite_member(organization, email, role, invited_by):
        email = email.lower()

        # Check if user is already a member
        if User.objects.filter(email=email, organization=organization, is_active=True).exists():
            raise ValueError('A user with this email is already a member of this organization.')

        # Check for pending invitation
        if TeamInvitation.objects.filter(
            organization=organization,
            email=email,
            status='pending',
            expires_at__gt=timezone.now(),
        ).exists():
            raise ValueError('A pending invitation already exists for this email.')

        invitation = TeamInvitation.objects.create(
            organization=organization,
            email=email,
            role=role,
            invited_by=invited_by,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(days=7),
        )

        # Log the invitation (email sending would go here in production)
        logger.info(
            f"Team invitation sent: {email} invited to {organization.name} "
            f"as {role} by {invited_by.email}, token: {invitation.token}"
        )

        ActivityLogService.log(
            organization=organization,
            user=invited_by,
            action='member_invited',
            target_email=email,
            details={'role': role},
        )

        return invitation

    @staticmethod
    def resend_invitation(invitation, resent_by):
        invitation.token = secrets.token_urlsafe(32)
        invitation.expires_at = timezone.now() + timedelta(days=7)
        invitation.save(update_fields=['token', 'expires_at', 'updated_at'])

        logger.info(
            f"Team invitation resent: {invitation.email} to {invitation.organization.name}, "
            f"token: {invitation.token}"
        )

        ActivityLogService.log(
            organization=invitation.organization,
            user=resent_by,
            action='invitation_resent',
            target_email=invitation.email,
        )

        return invitation

    @staticmethod
    def cancel_invitation(invitation, cancelled_by):
        invitation.status = 'cancelled'
        invitation.save(update_fields=['status', 'updated_at'])

        ActivityLogService.log(
            organization=invitation.organization,
            user=cancelled_by,
            action='invitation_cancelled',
            target_email=invitation.email,
        )

    @staticmethod
    @transaction.atomic
    def accept_invitation(token, first_name, last_name, password):
        try:
            invitation = TeamInvitation.objects.select_related('organization').get(token=token)
        except TeamInvitation.DoesNotExist:
            raise ValueError('Invalid invitation token.')

        if not invitation.is_valid:
            if invitation.is_expired:
                raise ValueError('This invitation has expired.')
            raise ValueError('This invitation is no longer valid.')

        # Check if a user with this email already exists
        existing_user = User.objects.filter(email=invitation.email).first()
        if existing_user:
            if existing_user.organization:
                raise ValueError('A user with this email is already a member of an organization.')
            # Reactivate existing user
            existing_user.organization = invitation.organization
            existing_user.role = invitation.role
            existing_user.first_name = first_name
            existing_user.last_name = last_name
            existing_user.is_active = True
            existing_user.set_password(password)
            existing_user.save()
            user = existing_user
        else:
            user = User.objects.create_user(
                email=invitation.email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                organization=invitation.organization,
                role=invitation.role,
            )

        # Update last_login since user is effectively logging in
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        invitation.status = 'accepted'
        invitation.accepted_by = user
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['status', 'accepted_by', 'accepted_at', 'updated_at'])

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        tokens = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        ActivityLogService.log(
            organization=invitation.organization,
            user=user,
            action='member_joined',
            target_email=invitation.email,
            details={'role': invitation.role},
        )

        return user, tokens

    @staticmethod
    def remove_member(target_user, removed_by):
        org = target_user.organization

        # Cannot remove yourself
        if target_user == removed_by:
            raise ValueError('You cannot remove yourself from the organization.')

        # Cannot remove sole owner
        if target_user.role == 'owner':
            owner_count = User.objects.filter(
                organization=org, role='owner', is_active=True
            ).count()
            if owner_count <= 1:
                raise ValueError('Cannot remove the sole owner of the organization.')

        target_user.organization = None
        target_user.is_active = False
        target_user.save(update_fields=['organization', 'is_active', 'updated_at'])

        ActivityLogService.log(
            organization=org,
            user=removed_by,
            action='member_removed',
            target_email=target_user.email,
            details={'role': target_user.role},
        )

    @staticmethod
    def change_role(target_user, new_role, changed_by):
        if new_role == 'owner':
            raise ValueError('Cannot assign owner role directly. Use transfer ownership instead.')

        org = target_user.organization

        # Cannot demote sole owner
        if target_user.role == 'owner':
            owner_count = User.objects.filter(
                organization=org, role='owner', is_active=True
            ).count()
            if owner_count <= 1:
                raise ValueError('Cannot change the role of the sole owner.')

        old_role = target_user.role
        target_user.role = new_role
        target_user.save(update_fields=['role', 'updated_at'])

        ActivityLogService.log(
            organization=org,
            user=changed_by,
            action='role_changed',
            target_email=target_user.email,
            details={'old_role': old_role, 'new_role': new_role},
        )

    @staticmethod
    @transaction.atomic
    def transfer_ownership(new_owner, current_owner):
        if new_owner == current_owner:
            raise ValueError('Cannot transfer ownership to yourself.')

        if new_owner.organization != current_owner.organization:
            raise ValueError('The target user must be in the same organization.')

        org = current_owner.organization

        new_owner.role = 'owner'
        new_owner.save(update_fields=['role', 'updated_at'])

        current_owner.role = 'admin'
        current_owner.save(update_fields=['role', 'updated_at'])

        ActivityLogService.log(
            organization=org,
            user=current_owner,
            action='ownership_transferred',
            target_email=new_owner.email,
            details={
                'new_owner': str(new_owner.id),
                'previous_owner': str(current_owner.id),
            },
        )
