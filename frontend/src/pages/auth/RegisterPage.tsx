import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { useAuthStore } from '@/stores/authStore';

export const RegisterPage = () => {
  const { isAuthenticated, _hasHydrated } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (_hasHydrated && isAuthenticated) {
      navigate('/contacts', { replace: true });
    }
  }, [_hasHydrated, isAuthenticated, navigate]);

  return (
    <AuthLayout
      title="Create an account"
      description="Get started with your email marketing platform"
    >
      <RegisterForm />
    </AuthLayout>
  );
};
