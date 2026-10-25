import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

interface LandlordRouteProps {
  children: React.ReactNode;
}

/**
 * Gates the landlord console on platform staff.
 *
 * `ProtectedRoute` only asks whether someone is signed in, and `role` is
 * organization-scoped — the owner of a tenant is not an operator of the
 * platform. This is the only client-side gate, and it is a convenience: the API
 * refuses non-staff independently, so a customer who navigates here by hand
 * sees an empty console rather than another tenant's data.
 */
export const LandlordRoute = ({ children }: LandlordRouteProps) => {
  const { user, isAuthenticated, accessToken, _hasHydrated } = useAuthStore();
  const location = useLocation();

  // Wait for the persisted store to rehydrate, or a refresh inside the console
  // bounces to the login screen before the token is read back.
  if (!_hasHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  const hasToken = accessToken || localStorage.getItem('access_token');
  if (!isAuthenticated && !hasToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Signed in but not staff: send them to their own dashboard rather than
  // showing a permission error for an area they have no reason to know exists.
  if (!user?.is_staff) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};
