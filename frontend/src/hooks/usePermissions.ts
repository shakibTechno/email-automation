import { useMemo } from 'react';
import { useAuthStore } from '@/stores/authStore';
import type { PlanType } from '@/types/billing';

/**
 * Plan tiers in ascending order, mirroring Organization.PLAN_RANK on the server.
 *
 * Gating asks "is this plan at least X". Answering that by listing tiers inline
 * is what left `isProfessionalOrAbove` as
 * `plan === 'professional' || plan === 'enterprise'` — omitting Business, which
 * ranks above Professional, so those customers lost features they had paid for.
 */
const PLAN_RANK: Record<PlanType, number> = {
  free: 0,
  starter: 1,
  professional: 2,
  business: 3,
  enterprise: 4,
};

/** True when `plan` is `minimum` or higher. An unknown plan fails closed. */
export function planAtLeast(plan: string | undefined, minimum: PlanType): boolean {
  const rank = PLAN_RANK[plan as PlanType];
  return rank !== undefined && rank >= PLAN_RANK[minimum];
}

export function usePermissions() {
  const user = useAuthStore((state) => state.user);
  const organization = useAuthStore((state) => state.organization);
  const plan = organization?.plan ?? 'free';
  const role = user?.role ?? 'viewer';

  const granted = useMemo(
    () => new Set(user?.permissions ?? []),
    [user?.permissions]
  );

  /**
   * Whether this user holds a permission, e.g. can('campaigns.send').
   *
   * The codes come from the API with the user, because a role name no longer
   * implies what it can do — a custom role is whatever set of codes its
   * organization gave it. This only decides what the UI offers; the API
   * enforces the same codes on every request.
   */
  const can = (code: string): boolean => {
    // The owner is never locked out of their own organization.
    if (role === 'owner') return true;
    // A session persisted before permissions were sent, until the profile
    // refetch lands. Falling back to the role name keeps the built-in roles
    // working rather than showing an admin a read-only app for a moment.
    if (user?.permissions === undefined) return role === 'admin';
    return granted.has(code);
  };

  return {
    can,
    isOwner: role === 'owner',
    isAdmin: can('team.manage'),
    canManageTeam: can('team.manage'),
    canTransferOwnership: role === 'owner',
    isProfessionalOrAbove: planAtLeast(plan, 'professional'),
    planAtLeast: (minimum: PlanType) => planAtLeast(plan, minimum),
  };
}
