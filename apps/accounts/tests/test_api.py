"""
Tests for accounts API endpoints.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.accounts.models import Organization, PasswordResetToken
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def organization():
    """Create a test organization."""
    return Organization.objects.create(
        name="Test Organization",
        email="org@test.com",
        plan="starter"
    )


@pytest.fixture
def user(organization):
    """Create a test user."""
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
        organization=organization,
        role="member"
    )


@pytest.fixture
def owner_user(organization):
    """Create an owner user."""
    return User.objects.create_user(
        email="owner@example.com",
        password="testpass123",
        first_name="Owner",
        last_name="User",
        organization=organization,
        role="owner"
    )


@pytest.mark.django_db
class TestRegistrationAPI:
    """Tests for user registration endpoint."""

    def test_register_success(self, api_client):
        """Test successful user registration."""
        url = reverse('accounts:register')
        data = {
            'email': 'newuser@example.com',
            'password': 'newpass123!@#',
            'password_confirm': 'newpass123!@#',
            'first_name': 'New',
            'last_name': 'User',
            'organization_name': 'New Company'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
        assert response.data['user']['email'] == 'newuser@example.com'

        # Verify user was created
        user = User.objects.get(email='newuser@example.com')
        assert user.first_name == 'New'
        assert user.last_name == 'User'
        assert user.role == 'owner'  # First user should be owner
        assert user.organization.name == 'New Company'

    def test_register_duplicate_email(self, api_client, user):
        """Test registration with duplicate email."""
        url = reverse('accounts:register')
        data = {
            'email': user.email,
            'password': 'newpass123!@#',
            'password_confirm': 'newpass123!@#',
            'first_name': 'New',
            'last_name': 'User',
            'organization_name': 'New Company'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch(self, api_client):
        """Test registration with mismatched passwords."""
        url = reverse('accounts:register')
        data = {
            'email': 'newuser@example.com',
            'password': 'newpass123!@#',
            'password_confirm': 'differentpass123!@#',
            'first_name': 'New',
            'last_name': 'User',
            'organization_name': 'New Company'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        """Test registration with weak password."""
        url = reverse('accounts:register')
        data = {
            'email': 'newuser@example.com',
            'password': '123',
            'password_confirm': '123',
            'first_name': 'New',
            'last_name': 'User',
            'organization_name': 'New Company'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginAPI:
    """Tests for user login endpoint."""

    def test_login_success(self, api_client, user):
        """Test successful login."""
        url = reverse('accounts:login')
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
        assert response.data['user']['email'] == user.email

    def test_login_invalid_credentials(self, api_client, user):
        """Test login with invalid credentials."""
        url = reverse('accounts:login')
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent user."""
        url = reverse('accounts:login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self, api_client, user):
        """Test login with inactive user."""
        user.is_active = False
        user.save()

        url = reverse('accounts:login')
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogoutAPI:
    """Tests for user logout endpoint."""

    def test_logout_success(self, api_client, user):
        """Test successful logout."""
        # First login to get tokens
        api_client.force_authenticate(user=user)
        login_url = reverse('accounts:login')
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data, format='json')
        refresh_token = login_response.data['tokens']['refresh']

        # Logout
        logout_url = reverse('accounts:logout')
        logout_data = {'refresh': refresh_token}
        response = api_client.post(logout_url, logout_data, format='json')

        assert response.status_code == status.HTTP_205_RESET_CONTENT

    def test_logout_without_token(self, api_client, user):
        """Test logout without refresh token."""
        api_client.force_authenticate(user=user)
        url = reverse('accounts:logout')
        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_unauthenticated(self, api_client):
        """Test logout without authentication."""
        url = reverse('accounts:logout')
        response = api_client.post(url, {'refresh': 'fake-token'}, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProfileAPI:
    """Tests for user profile endpoint."""

    def test_get_profile(self, api_client, user):
        """Test getting user profile."""
        api_client.force_authenticate(user=user)
        url = reverse('accounts:profile')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['first_name'] == user.first_name
        assert response.data['last_name'] == user.last_name

    def test_get_profile_unauthenticated(self, api_client):
        """Test getting profile without authentication."""
        url = reverse('accounts:profile')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile(self, api_client, user):
        """Test updating user profile."""
        api_client.force_authenticate(user=user)
        url = reverse('accounts:profile')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '+1234567890'
        }
        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'
        assert response.data['last_name'] == 'Name'
        assert response.data['phone'] == '+1234567890'

        # Verify database was updated
        user.refresh_from_db()
        assert user.first_name == 'Updated'
        assert user.last_name == 'Name'
        assert user.phone == '+1234567890'


@pytest.mark.django_db
class TestChangePasswordAPI:
    """Tests for change password endpoint."""

    def test_change_password_success(self, api_client, user):
        """Test successful password change."""
        api_client.force_authenticate(user=user)
        url = reverse('accounts:change-password')
        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass123!@#',
            'new_password_confirm': 'newpass123!@#'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Verify password was changed
        user.refresh_from_db()
        assert user.check_password('newpass123!@#')

    def test_change_password_wrong_old_password(self, api_client, user):
        """Test changing password with wrong old password."""
        api_client.force_authenticate(user=user)
        url = reverse('accounts:change-password')
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'newpass123!@#',
            'new_password_confirm': 'newpass123!@#'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_mismatch(self, api_client, user):
        """Test changing password with mismatched new passwords."""
        api_client.force_authenticate(user=user)
        url = reverse('accounts:change-password')
        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass123!@#',
            'new_password_confirm': 'differentpass123!@#'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPasswordResetAPI:
    """Tests for password reset endpoints."""

    def test_request_password_reset(self, api_client, user):
        """Test requesting password reset."""
        url = reverse('accounts:password-reset')
        data = {'email': user.email}
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Verify token was created
        assert PasswordResetToken.objects.filter(user=user).exists()

    def test_request_password_reset_nonexistent_email(self, api_client):
        """Test requesting password reset for non-existent email."""
        url = reverse('accounts:password-reset')
        data = {'email': 'nonexistent@example.com'}
        response = api_client.post(url, data, format='json')

        # Should still return success for security
        assert response.status_code == status.HTTP_200_OK

    def test_confirm_password_reset(self, api_client, user):
        """Test confirming password reset."""
        # Create reset token
        token = PasswordResetToken.objects.create(
            user=user,
            token='test-reset-token',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        url = reverse('accounts:password-reset-confirm')
        data = {
            'token': token.token,
            'new_password': 'newpass123!@#',
            'new_password_confirm': 'newpass123!@#'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Verify password was changed
        user.refresh_from_db()
        assert user.check_password('newpass123!@#')

        # Verify token was marked as used
        token.refresh_from_db()
        assert token.is_used is True

    def test_confirm_password_reset_invalid_token(self, api_client):
        """Test confirming password reset with invalid token."""
        url = reverse('accounts:password-reset-confirm')
        data = {
            'token': 'invalid-token',
            'new_password': 'newpass123!@#',
            'new_password_confirm': 'newpass123!@#'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirm_password_reset_expired_token(self, api_client, user):
        """Test confirming password reset with expired token."""
        # Create expired token
        token = PasswordResetToken.objects.create(
            user=user,
            token='expired-token',
            expires_at=timezone.now() - timedelta(hours=1)
        )

        url = reverse('accounts:password-reset-confirm')
        data = {
            'token': token.token,
            'new_password': 'newpass123!@#',
            'new_password_confirm': 'newpass123!@#'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTokenRefreshAPI:
    """Tests for token refresh endpoint."""

    def test_refresh_token(self, api_client, user):
        """Test refreshing access token."""
        # Login to get tokens
        login_url = reverse('accounts:login')
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data, format='json')
        refresh_token = login_response.data['tokens']['refresh']

        # Refresh token
        refresh_url = reverse('accounts:token-refresh')
        refresh_data = {'refresh': refresh_token}
        response = api_client.post(refresh_url, refresh_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_refresh_token_invalid(self, api_client):
        """Test refreshing with invalid token."""
        url = reverse('accounts:token-refresh')
        data = {'refresh': 'invalid-token'}
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
