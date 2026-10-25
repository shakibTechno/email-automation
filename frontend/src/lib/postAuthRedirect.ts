import type { User } from '@/types/auth';

/**
 * Where a user lands once they are signed in.
 *
 * One function because three call sites needed the answer — login success,
 * registration success, and the login page's "already signed in" effect — and
 * all three had `/contacts` hardcoded, a leftover from when contacts was the
 * only screen in the product. A platform operator sent there gets a 403 wall:
 * they belong to no tenant.
 */
export const landingPathFor = (user?: User | null): string => {
  if (user?.is_staff && !user.organization) return '/landlord';
  return '/dashboard';
};

/**
 * `ProtectedRoute` records where someone was heading before being bounced to
 * the login screen; honouring it is the whole point of recording it. Anything
 * under the auth routes is ignored, or signing in would send them back to the
 * form they just submitted.
 */
const AUTH_PATHS = ['/login', '/register', '/forgot-password', '/accept-invitation'];

export const resolveRedirect = (user: User | null | undefined, from?: unknown): string => {
  const fallback = landingPathFor(user);

  const path =
    typeof from === 'string'
      ? from
      : typeof (from as { pathname?: unknown })?.pathname === 'string'
        ? (from as { pathname: string }).pathname
        : null;

  if (!path || !path.startsWith('/') || AUTH_PATHS.some((p) => path.startsWith(p))) {
    return fallback;
  }

  // An operator has no tenant screens to return to, so a remembered tenant
  // path is worse than the console they can actually use.
  if (fallback === '/landlord' && !path.startsWith('/landlord')) return fallback;

  return path;
};
