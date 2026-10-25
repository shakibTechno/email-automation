import { useAuthStore } from '@/stores/authStore';
import type { UserRole } from '@/types/team';
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
  const role = (user?.role as UserRole) || 'viewer';
  const plan = organization?.plan ?? 'free';

  return {
    role,
    isOwner: role === 'owner',
    isAdmin: role === 'owner' || role === 'admin',
    canCreate: role !== 'viewer',
    canEdit: role !== 'viewer',
    canDelete: role === 'owner' || role === 'admin',
    canManageTeam: role === 'owner' || role === 'admin',
    canTransferOwnership: role === 'owner',
    isProfessionalOrAbove: planAtLeast(plan, 'professional'),
    planAtLeast: (minimum: PlanType) => planAtLeast(plan, minimum),
  };
}
