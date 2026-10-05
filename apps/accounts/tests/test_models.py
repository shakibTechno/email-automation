"""
Tests for accounts models.
"""
import pytest
from django.contrib.auth import get_user_model
from apps.accounts.models import Organization, PasswordResetToken
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationModel:
    """Tests for Organization model."""

    def test_create_organization(self):
        """Test creating an organization."""
        org = Organization.objects.create(
            name="Test Company",
            email="test@company.com",
            plan="starter"
        )
        assert org.name == "Test Company"
        assert org.slug == "test-company"
        assert org.plan == "starter"
        assert org.is_active is True

    def test_organization_slug_auto_generation(self):
        """Test that slug is auto-generated from name."""
        org = Organization.objects.create(name="My Test Organization")
        assert org.slug == "my-test-organization"

    def test_organization_slug_uniqueness(self):
        """Test that duplicate organization names get unique slugs."""
        org1 = Organization.objects.create(name="Test Org")
        org2 = Organization.objects.create(name="Test Org")
        assert org1.slug == "test-org"
        assert org2.slug == "test-org-1"

    def test_organization_soft_delete(self):
        """Test soft delete functionality."""
        org = Organization.objects.create(name="Test Delete")
        org.soft_delete()
        assert org.is_deleted is True
        assert org.deleted_at is not None

    def test_organization_restore(self):
        """Test restore functionality."""
        org = Organization.objects.create(name="Test Restore")
        org.soft_delete()
        org.restore()
        assert org.is_deleted is False
        assert org.deleted_at is None


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model."""

    def test_create_user(self):
        """Test creating a regular user."""
        org = Organization.objects.create(name="Test Org")
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            organization=org
        )
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User"
        )
        assert user.email == "admin@example.com"
        assert user.is_active is True
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == "owner"

    def test_user_email_normalization(self):
        """Test that email is normalized."""
        org = Organization.objects.create(name="Test Org")
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM",
            password="testpass123",
            organization=org
        )
        assert user.email == "Test@example.com"

    def test_user_full_name(self):
        """Test full_name property."""
        org = Organization.objects.create(name="Test Org")
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            organization=org
        )
        assert user.full_name == "John Doe"

    def test_user_full_name_no_names(self):
        """Test full_name property when names are empty."""
        org = Organization.objects.create(name="Test Org")
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            organization=org
        )
        assert user.full_name == "test@example.com"

    def test_is_organization_owner(self):
        """Test is_organization_owner property."""
        org = Organization.objects.create(name="Test Org")
        owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            organization=org,
            role="owner"
        )
        member = User.objects.create_user(
            email="member@example.com",
            password="testpass123",
            organization=org,
            role="member"
        )
        assert owner.is_organization_owner is True
        assert member.is_organization_owner is False

    def test_is_organization_admin(self):
        """Test is_organization_admin property."""
        org = Organization.objects.create(name="Test Org")
        owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            organization=org,
            role="owner"
        )
        admin = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            organization=org,
            role="admin"
        )
        member = User.objects.create_user(
            email="member@example.com",
            password="testpass123",
            organization=org,
            role="member"
        )
        assert owner.is_organization_admin is True
        assert admin.is_organization_admin is True
        assert member.is_organization_admin is False


@pytest.mark.django_db
class TestPasswordResetToken:
    """Tests for PasswordResetToken model."""

    def test_create_password_reset_token(self):
        """Test creating a password reset token."""
        org = Organization.objects.create(name="Test Org")
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            organization=org
        )
        token = PasswordResetToken.objects.create(
            user=user,
            token="test-token-123",
            expires_at=timezone.now() + timedelta(hours=1)
        )
        assert token.user == user
        assert token.is_used is False
        assert token.is_expired is False
        assert token.is_valid is True

    def test_password_reset_token_expired(self):
        """Test expired password reset token."""
        org = Organization.objects.create(name="Test Org")
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            organization=org
        )
        token = PasswordResetToken.objects.create(
            user=user,
            token="test-token-123",
            expires_at=timezone.now() - timedelta(hours=1)
        )
        assert token.is_expired is True
        assert token.is_valid is False

    def test_password_reset_token_used(self):
        """Test used password reset token."""
        org = Organization.objects.create(name="Test Org")
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            organization=org
        )
        token = PasswordResetToken.objects.create(
            user=user,
            token="test-token-123",
            expires_at=timezone.now() + timedelta(hours=1),
            is_used=True
        )
        assert token.is_used is True
        assert token.is_valid is False
