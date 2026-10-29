"""
Services for team management and activity logging.
"""
import secrets
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.mail import MailResult, send_transactional_email

from .models import (
    ActivityLog, EmailVerificationToken, Organization, TeamInvitation,
)

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

        # Not logged with the token. The old line here wrote it in plaintext,
        # which made every application log a list of live invitations anyone
        # with log access could accept.
        logger.info(
            "Team invitation created: %s invited to %s as %s by %s",
            email, organization.name, role, invited_by.email,
        )

        TeamService.send_invitation_email(invitation)

        ActivityLogService.log(
            organization=organization,
            user=invited_by,
            action='member_invited',
            target_email=email,
            details={'role': role, 'email_sent': invitation.email_sent_at is not None},
        )

        return invitation

    @staticmethod
    def send_invitation_email(invitation):
        """
        Send the invitation. Returns whether the provider accepted it.

        Reported rather than raised: the invitation row is already valid and the
        link already works, so a failed send must not undo it. The admin is told
        instead, and given the link to pass on by hand — which is the difference
        between a feature that degrades and one that silently does nothing.
        """
        organization = invitation.organization
        inviter = invitation.invited_by
        inviter_name = (
            (inviter.full_name or inviter.email) if inviter else organization.name
        )
        # TeamInvitation has its own narrower ROLE_CHOICES (no 'owner'), which
        # is the right source for a label on an invitation.
        role_label = dict(TeamInvitation.ROLE_CHOICES).get(invitation.role, invitation.role)

        result = send_transactional_email(
            subject=f'{inviter_name} invited you to {organization.name}',
            template='accounts/email/team_invitation',
            to_email=invitation.email,
            organization=organization,
            # Account mail: it is about joining the platform and links to it,
            # so it goes out on the platform's domain rather than the
            # organization's. A new organization has no verified domain yet,
            # and inviting the rest of the team is one of the first things it
            # does.
            from_platform=True,
            # The domain is the platform's; the name is not. "Ada at Acme" is
            # what the recipient recognises, and recognition is the whole job
            # of an invitation's From line.
            sender_name=f'{inviter_name} at {organization.name}',
            # Replies go to the person who invited them, not to a noreply
            # address: the first question a recipient has is "is this real",
            # and the answer is a reply to the colleague who sent it.
            reply_to=((inviter.reply_to_email or inviter.email)
                      if inviter else None),
            context={
                'product_name': settings.APP_NAME,
                'organization_name': organization.name,
                'inviter_name': inviter_name,
                'inviter_email': inviter.email if inviter else '',
                'role_label': role_label,
                'role_article': 'an' if role_label[:1].lower() in 'aeiou' else 'a',
                'accept_url': TeamService.invitation_url(invitation),
                'expires_at': invitation.expires_at,
            },
        )

        invitation.email_sent_at = timezone.now() if result.ok else None
        invitation.email_error = result.error
        invitation.save(update_fields=['email_sent_at', 'email_error', 'updated_at'])
        return result.ok

    @staticmethod
    def invitation_url(invitation):
        """
        The link the recipient follows.

        Points at the SPA route that collects their name and password
        (`/accept-invitation?token=`), not at the API — the token is useless
        without that form.
        """
        frontend = settings.FRONTEND_URL.rstrip('/')
        return f'{frontend}/accept-invitation?token={invitation.token}'

    @staticmethod
    def resend_invitation(invitation, resent_by):
        invitation.token = secrets.token_urlsafe(32)
        invitation.expires_at = timezone.now() + timedelta(days=7)
        invitation.save(update_fields=['token', 'expires_at', 'updated_at'])

        # Again, no token in the log line.
        logger.info(
            "Team invitation resent: %s to %s",
            invitation.email, invitation.organization.name,
        )

        TeamService.send_invitation_email(invitation)

        ActivityLogService.log(
            organization=invitation.organization,
            user=resent_by,
            action='invitation_resent',
            target_email=invitation.email,
            details={'email_sent': invitation.email_sent_at is not None},
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


class AccountEmailService:
    """
    The two account emails that prove someone owns an address.

    Both are platform mail: they are about this account, they link to this
    platform, and they must work for an organization that has verified no
    sending domain of its own -- which is every organization on the day it
    signs up, and exactly when these are sent.

    Neither raises. A registration must still succeed when the mail fails, and
    a password reset request must answer the same way whether or not the
    address exists; the return value is how the caller tells the truth without
    telling the sender anything about who has an account.
    """

    RESET_TTL = timedelta(hours=1)
    # Longer than a reset, because nothing is at risk while it is unused and a
    # confirmation mail is often read the next day.
    VERIFICATION_TTL = timedelta(days=3)

    @staticmethod
    def reset_url(token):
        """The SPA route that collects the new password, not the API."""
        return f'{settings.FRONTEND_URL.rstrip("/")}/reset-password?token={token}'

    @staticmethod
    def verify_url(token):
        return f'{settings.FRONTEND_URL.rstrip("/")}/verify-email?token={token}'

    @staticmethod
    def send_password_reset(reset_token):
        """Send the reset link. Returns MailResult."""
        user = reset_token.user
        result = send_transactional_email(
            subject=f'Reset your {settings.APP_NAME} password',
            template='accounts/email/password_reset',
            to_email=user.email,
            organization=user.organization,
            from_platform=True,
            context={
                'product_name': settings.APP_NAME,
                'user_email': user.email,
                'reset_url': AccountEmailService.reset_url(reset_token.token),
                'expires_at': reset_token.expires_at,
            },
        )
        if not result.ok:
            # Logged without the token: this message carries a credential, and
            # a traceback with one in it is a credential in the log file.
            logger.error(
                'Password reset email to %s failed: %s', user.email, result.error
            )
        return result

    @staticmethod
    def send_verification(user):
        """
        Issue a fresh verification token and send it. Returns MailResult.

        Earlier unused tokens are spent first, so a resend invalidates the link
        in the previous email rather than leaving several live at once.
        """
        if user.is_email_verified:
            return MailResult(True, '')

        EmailVerificationToken.objects.filter(
            user=user, is_used=False
        ).update(is_used=True)

        token = EmailVerificationToken.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + AccountEmailService.VERIFICATION_TTL,
        )

        organization = user.organization
        result = send_transactional_email(
            subject='Confirm your email address',
            template='accounts/email/email_verification',
            to_email=user.email,
            organization=organization,
            from_platform=True,
            context={
                'product_name': settings.APP_NAME,
                'first_name': user.first_name,
                'organization_name': organization.name if organization else settings.APP_NAME,
                'verify_url': AccountEmailService.verify_url(token.token),
                'expires_at': token.expires_at,
            },
        )
        if not result.ok:
            logger.error(
                'Verification email to %s failed: %s', user.email, result.error
            )
        return result

    @staticmethod
    @transaction.atomic
    def verify(raw_token):
        """
        Spend a verification token. Returns the user, or None.

        None covers unknown, expired and already-spent alike: telling an
        anonymous caller which one it was says whether an address has an
        account here.
        """
        token = (
            EmailVerificationToken.objects
            .select_for_update()
            .select_related('user')
            .filter(token=raw_token)
            .first()
        )
        if token is None or not token.is_valid:
            return None

        token.is_used = True
        token.save(update_fields=['is_used'])

        user = token.user
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])
        logger.info('Email verified for %s', user.email)
        return user
