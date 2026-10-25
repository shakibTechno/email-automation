import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { user, isAuthenticated, accessToken, _hasHydrated } = useAuthStore();
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

  // Platform staff belong to no tenant, so every screen in here would ask the
  // API for an organization they do not have and render a wall of errors. Send
  // them to the console that is actually theirs. Staff who also own a tenant
  // (the bootstrap account does) keep the normal app. Their own profile and
  // password live at /landlord/profile, inside the console's own shell.
  if (user?.is_staff && !user.organization) {
    return <Navigate to="/landlord" replace />;
  }

  return <>{children}</>;
};
