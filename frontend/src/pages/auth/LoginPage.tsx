import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { LoginForm } from '@/components/auth/LoginForm';
import { useAuthStore } from '@/stores/authStore';
import { resolveRedirect } from '@/lib/postAuthRedirect';

export const LoginPage = () => {
  const { user, isAuthenticated, _hasHydrated } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Only redirect after Zustand has rehydrated from localStorage
    if (_hasHydrated && isAuthenticated) {
      navigate(resolveRedirect(user, (location.state as { from?: unknown })?.from), {
        replace: true,
      });
    }
  }, [_hasHydrated, isAuthenticated, user, location.state, navigate]);

  return (
    <AuthLayout
      title="Welcome back"
      description="Sign in to your account to continue"
    >
      <LoginForm />
    </AuthLayout>
  );
};
