import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isAuthenticated, accessToken, _hasHydrated } = useAuthStore();
  const location = useLocation();

  // Wait for Zustand to rehydrate from localStorage
  if (!_hasHydrated) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  // Check both isAuthenticated flag and token existence
  const hasToken = accessToken || localStorage.getItem('access_token');

  if (!isAuthenticated && !hasToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
