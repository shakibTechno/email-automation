"""
URL configuration for accounts app.
"""
from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    ProfileView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    EmailVerificationView,
    ResendVerificationView,
    TokenRefreshView,
)

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

    # Password Reset
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # Email verification
    path('verify-email/', EmailVerificationView.as_view(), name='verify-email'),
    path('verify-email/resend/', ResendVerificationView.as_view(), name='verify-email-resend'),
]
