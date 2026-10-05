import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { LoginForm } from '@/components/auth/LoginForm';
import { useAuthStore } from '@/stores/authStore';

export const LoginPage = () => {
  const { isAuthenticated, _hasHydrated } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    // Only redirect after Zustand has rehydrated from localStorage
    if (_hasHydrated && isAuthenticated) {
      navigate('/contacts', { replace: true });
    }
  }, [_hasHydrated, isAuthenticated, navigate]);

  return (
    <AuthLayout
      title="Welcome back"
      description="Sign in to your account to continue"
    >
      <LoginForm />
    </AuthLayout>
  );
};
