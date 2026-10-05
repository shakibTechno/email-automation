import { useAuthStore } from '@/stores/authStore';
import type { UserRole } from '@/types/team';

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
    isProfessionalOrAbove: plan === 'professional' || plan === 'enterprise',
  };
}
