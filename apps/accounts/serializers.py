"""
Serializers for accounts app.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from .models import User, Organization, PasswordResetToken, TeamInvitation, ActivityLog, EmailConfiguration
import secrets


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model."""

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'domain', 'plan', 'is_active',
            'email', 'phone', 'address_line1', 'address_line2',
            'city', 'state', 'country', 'postal_code',
            'max_contacts', 'max_emails_per_month',
            'tracking_key',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'tracking_key', 'created_at', 'updated_at',
        ]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    organization = OrganizationSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'organization', 'role', 'is_active', 'is_email_verified',
            # Platform staff, who have no organization and use the landlord
            # console instead of the tenant app. The frontend has no other way
            # to tell the two apart — `role` is organization-scoped.
            'is_staff',
            'phone', 'avatar', 'timezone', 'language', 'reply_to_email',
            'created_at', 'updated_at', 'last_login'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_login',
            'is_email_verified', 'is_staff',
        ]


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration."""
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    organization_name = serializers.CharField(max_length=255)

    # Optional fields
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=50, required=False, default='UTC')
    language = serializers.CharField(max_length=10, required=False, default='en')

    def validate_email(self, value):
        """Validate that email is unique."""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, data):
        """Validate that passwords match."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match."
            })
        return data

    def create(self, validated_data):
        """Create user and organization."""
        # Remove password_confirm
        validated_data.pop('password_confirm')

        # Extract organization name
        organization_name = validated_data.pop('organization_name')

        # Create organization
        organization = Organization.objects.create(
            name=organization_name,
            email=validated_data['email']
        )

        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            organization=organization,
            role='owner',  # First user is the owner
            phone=validated_data.get('phone', ''),
            timezone=validated_data.get('timezone', 'UTC'),
            language=validated_data.get('language', 'en')
        )

        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Validate credentials and return user."""
        email = data.get('email', '').lower()
        password = data.get('password', '')

        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")

        # Authenticate user
        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        if user.deleted_at:
            raise serializers.ValidationError("User account has been deleted.")

        # Account-level suspension. Platform staff have no organization and are
        # unaffected — otherwise suspending a tenant could lock out the operator
        # who needs to unsuspend it.
        organization = getattr(user, 'organization', None)
        if organization is not None and not organization.is_active:
            reason = (organization.suspension_reason or '').strip()
            raise serializers.ValidationError(
                f"This account has been suspended. {reason}".strip()
                if reason else
                "This account has been suspended. Contact support to restore access."
            )

        data['user'] = user
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        """Validate old password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        """Validate that new passwords match."""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "New passwords do not match."
            })
        return data

    def save(self):
        """Update user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting password reset."""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate that user exists."""
        try:
            user = User.objects.get(email=value.lower(), is_active=True)
            self.context['user'] = user
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            pass
        return value.lower()

    def save(self):
        """Create password reset token."""
        user = self.context.get('user')
        if not user:
            # Return None if user doesn't exist (security)
            return None

        # Generate token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=1)

        # Create password reset token
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

        return reset_token


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset."""
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_token(self, value):
        """Validate reset token."""
        try:
            reset_token = PasswordResetToken.objects.get(token=value)
            if not reset_token.is_valid:
                raise serializers.ValidationError("Invalid or expired reset token.")
            self.context['reset_token'] = reset_token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid reset token.")
        return value

    def validate(self, data):
        """Validate that passwords match."""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Passwords do not match."
            })
        return data

    def save(self):
        """Reset user password."""
        reset_token = self.context['reset_token']
        user = reset_token.user

        # Update password
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])

        # Mark token as used
        reset_token.is_used = True
        reset_token.save(update_fields=['is_used'])

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'avatar',
            'timezone', 'language', 'reply_to_email',
        ]

    def validate_avatar(self, value):
        """Validate avatar URL."""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Avatar must be a valid URL.")
        return value


# --- Team Management Serializers ---

class TeamMemberSerializer(serializers.ModelSerializer):
    """Read-only serializer for team member listing."""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_active', 'last_login', 'created_at',
        ]
        read_only_fields = fields


class InviteMemberSerializer(serializers.Serializer):
    """Serializer for inviting a new team member."""
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=[
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ])


class ChangeRoleSerializer(serializers.Serializer):
    """Serializer for changing a member's role."""
    role = serializers.ChoiceField(choices=[
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ])


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer for accepting a team invitation."""
    token = serializers.CharField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match."
            })
        return data


class TeamInvitationSerializer(serializers.ModelSerializer):
    """Serializer for team invitation details."""
    invited_by_name = serializers.SerializerMethodField()
    email_sent = serializers.SerializerMethodField()
    accept_url = serializers.SerializerMethodField()

    class Meta:
        model = TeamInvitation
        fields = [
            'id', 'email', 'role', 'status', 'invited_by_name',
            'email_sent', 'email_sent_at', 'email_error', 'accept_url',
            'expires_at', 'created_at',
        ]
        read_only_fields = fields

    def get_email_sent(self, obj):
        return obj.email_sent_at is not None

    def get_accept_url(self, obj):
        """
        The link, so an admin can pass it on when the email did not arrive.

        Only for an invitation that is still usable, and only to someone who can
        already see the invitation — an organization admin, per the view's
        permissions. Handing it out for an accepted or cancelled invitation
        would be a live credential for nothing.
        """
        if obj.status != 'pending' or not obj.is_valid:
            return None
        from .services import TeamService

        return TeamService.invitation_url(obj)

    def get_invited_by_name(self, obj):
        if obj.invited_by:
            return obj.invited_by.full_name
        return None


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for activity log entries."""
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'action', 'user_name', 'target_email',
            'details', 'created_at',
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.full_name
        return None


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating organization settings."""

    class Meta:
        model = Organization
        fields = [
            'name', 'domain', 'email', 'phone',
            'address_line1', 'address_line2', 'city',
            'state', 'country', 'postal_code',
        ]


class TransferOwnershipSerializer(serializers.Serializer):
    """Serializer for transferring organization ownership."""
    new_owner_id = serializers.UUIDField()


# --- Email Configuration Serializers ---

class EmailConfigurationSerializer(serializers.ModelSerializer):
    """Full serializer — admin/owner only (includes SMTP engine fields)."""

    class Meta:
        model = EmailConfiguration
        fields = [
            'default_sender_name', 'default_sender_email', 'default_reply_to_email',
            'backend', 'smtp_host', 'smtp_port', 'smtp_use_ssl', 'smtp_use_tls',
            'smtp_username', 'smtp_password', 'smtp_from_email',
        ]

    def validate(self, attrs):
        use_ssl = attrs.get('smtp_use_ssl', self.instance.smtp_use_ssl if self.instance else True)
        use_tls = attrs.get('smtp_use_tls', self.instance.smtp_use_tls if self.instance else False)
        if use_ssl and use_tls:
            raise serializers.ValidationError(
                'smtp_use_ssl and smtp_use_tls are mutually exclusive.'
            )
        return attrs


class EmailSenderConfigSerializer(serializers.ModelSerializer):
    """Limited serializer — any member (sender defaults only, no SMTP secrets)."""

    class Meta:
        model = EmailConfiguration
        fields = [
            'default_sender_name', 'default_sender_email', 'default_reply_to_email',
        ]


class EmailVerificationSerializer(serializers.Serializer):
    """The token from a confirmation link."""
    token = serializers.CharField(max_length=255)
