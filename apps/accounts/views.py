"""
Views for accounts app.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse
from apps.core.permissions import IsOrganizationMember, IsOrganizationAdmin, IsOrganizationOwner
from .models import TeamInvitation
from .services import TeamService, ActivityLogService
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    TeamMemberSerializer,
    InviteMemberSerializer,
    ChangeRoleSerializer,
    AcceptInvitationSerializer,
    TeamInvitationSerializer,
    ActivityLogSerializer,
    OrganizationUpdateSerializer,
    OrganizationSerializer,
    TransferOwnershipSerializer,
)
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def get_tokens_for_user(user):
    """Generate JWT tokens for user."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    Creates a new user and organization.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={
            201: OpenApiResponse(
                response=UserSerializer,
                description='User successfully registered'
            ),
            400: OpenApiResponse(description='Bad request')
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Update last_login timestamp
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Generate tokens
        tokens = get_tokens_for_user(user)

        # Serialize user data
        user_data = UserSerializer(user).data

        logger.info(f"New user registered: {user.email}")

        return Response({
            'user': user_data,
            'tokens': tokens,
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    API endpoint for user login.
    Returns JWT tokens on successful authentication.
    """
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description='Login successful'
            ),
            400: OpenApiResponse(description='Invalid credentials')
        }
    )
    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Update last_login timestamp
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Generate tokens
        tokens = get_tokens_for_user(user)

        # Serialize user data
        user_data = UserSerializer(user).data

        logger.info(f"User logged in: {user.email}")

        return Response({
            'user': user_data,
            'tokens': tokens,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    API endpoint for user logout.
    Blacklists the refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string'}
                },
                'required': ['refresh']
            }
        },
        responses={
            205: OpenApiResponse(description='Logout successful'),
            400: OpenApiResponse(description='Bad request')
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            logger.info(f"User logged out: {request.user.email}")

            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_205_RESET_CONTENT
            )
        except (TokenError, InvalidToken) as e:
            logger.error(f"Logout error: {str(e)}")
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for retrieving and updating user profile.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description='User profile retrieved'
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description='Profile updated successfully'
            ),
            400: OpenApiResponse(description='Bad request')
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description='Profile updated successfully'
            ),
            400: OpenApiResponse(description='Bad request')
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """
    API endpoint for changing user password.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description='Password changed successfully'),
            400: OpenApiResponse(description='Bad request')
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(f"Password changed for user: {request.user.email}")

        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )


class PasswordResetRequestView(APIView):
    """
    API endpoint for requesting password reset.
    Sends reset email with token.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(description='Reset email sent if user exists'),
            400: OpenApiResponse(description='Bad request')
        }
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_token = serializer.save()

        if reset_token:
            # TODO: Send email with reset link
            # For now, we'll just log it
            logger.info(
                f"Password reset requested for: {reset_token.user.email}, "
                f"token: {reset_token.token}"
            )

        # Always return success for security (don't reveal if email exists)
        return Response(
            {
                'message': 'If a user with that email exists, '
                          'a password reset link has been sent.'
            },
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """
    API endpoint for confirming password reset.
    Validates token and updates password.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(description='Password reset successful'),
            400: OpenApiResponse(description='Bad request')
        }
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        logger.info(f"Password reset completed for user: {user.email}")

        return Response(
            {'message': 'Password reset successful'},
            status=status.HTTP_200_OK
        )


class TokenRefreshView(TokenRefreshView):
    """
    API endpoint for refreshing JWT access token.
    """
    @extend_schema(
        responses={
            200: OpenApiResponse(description='Token refreshed successfully'),
            401: OpenApiResponse(description='Invalid or expired token')
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# --- Team Management Views ---

class TeamMemberListView(APIView):
    """List all team members in the organization."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        members = TeamService.list_members(request.user.organization)
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)


class InviteMemberView(APIView):
    """Invite a new member to the organization."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invitation = TeamService.invite_member(
                organization=request.user.organization,
                email=serializer.validated_data['email'],
                role=serializer.validated_data['role'],
                invited_by=request.user,
            )
            return Response(
                TeamInvitationSerializer(invitation).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InvitationListView(APIView):
    """List pending invitations for the organization."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]

    def get(self, request):
        invitations = TeamInvitation.objects.filter(
            organization=request.user.organization,
            status='pending',
        ).select_related('invited_by').order_by('-created_at')
        serializer = TeamInvitationSerializer(invitations, many=True)
        return Response(serializer.data)


class ResendInvitationView(APIView):
    """Resend a pending invitation."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, invitation_id):
        try:
            invitation = TeamInvitation.objects.get(
                id=invitation_id,
                organization=request.user.organization,
                status='pending',
            )
        except TeamInvitation.DoesNotExist:
            return Response(
                {'error': 'Invitation not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        TeamService.resend_invitation(invitation, request.user)
        return Response(TeamInvitationSerializer(invitation).data)


class CancelInvitationView(APIView):
    """Cancel a pending invitation."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]

    def delete(self, request, invitation_id):
        try:
            invitation = TeamInvitation.objects.get(
                id=invitation_id,
                organization=request.user.organization,
                status='pending',
            )
        except TeamInvitation.DoesNotExist:
            return Response(
                {'error': 'Invitation not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        TeamService.cancel_invitation(invitation, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AcceptInvitationView(APIView):
    """Accept a team invitation (public endpoint)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, tokens = TeamService.accept_invitation(
                token=serializer.validated_data['token'],
                first_name=serializer.validated_data['first_name'],
                last_name=serializer.validated_data['last_name'],
                password=serializer.validated_data['password'],
            )
            user_data = UserSerializer(user).data
            return Response({
                'user': user_data,
                'tokens': tokens,
                'message': 'Invitation accepted successfully.',
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RemoveMemberView(APIView):
    """Remove a member from the organization."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]

    def delete(self, request, member_id):
        try:
            target_user = User.objects.get(
                id=member_id,
                organization=request.user.organization,
                is_active=True,
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'Member not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            TeamService.remove_member(target_user, request.user)
            return Response(
                {'message': 'Member removed successfully.'},
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ChangeRoleView(APIView):
    """Change a member's role."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]

    def patch(self, request, member_id):
        try:
            target_user = User.objects.get(
                id=member_id,
                organization=request.user.organization,
                is_active=True,
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'Member not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            TeamService.change_role(
                target_user,
                serializer.validated_data['role'],
                request.user,
            )
            return Response(TeamMemberSerializer(target_user).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TransferOwnershipView(APIView):
    """Transfer organization ownership to another member."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationOwner]

    def post(self, request):
        serializer = TransferOwnershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            new_owner = User.objects.get(
                id=serializer.validated_data['new_owner_id'],
                organization=request.user.organization,
                is_active=True,
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found in this organization.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            TeamService.transfer_ownership(new_owner, request.user)
            return Response({
                'message': 'Ownership transferred successfully.',
                'new_owner': TeamMemberSerializer(new_owner).data,
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ActivityLogView(APIView):
    """View activity log for the organization."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]

    def get(self, request):
        limit = int(request.query_params.get('limit', 50))
        logs = ActivityLogService.get_recent(request.user.organization, limit)
        serializer = ActivityLogSerializer(logs, many=True)
        return Response(serializer.data)


class OrganizationSettingsView(APIView):
    """View and update organization settings."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        serializer = OrganizationSerializer(request.user.organization)
        return Response(serializer.data)

    def patch(self, request):
        # Only admin/owner can update
        if request.user.role not in ('admin', 'owner'):
            return Response(
                {'error': 'You do not have permission to update organization settings.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = OrganizationUpdateSerializer(
            request.user.organization,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        ActivityLogService.log(
            organization=request.user.organization,
            user=request.user,
            action='org_settings_updated',
            details={'fields': list(request.data.keys())},
        )

        return Response(OrganizationSerializer(request.user.organization).data)
