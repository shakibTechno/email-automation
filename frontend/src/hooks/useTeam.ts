import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as teamApi from '@/api/team';
import type {
  InviteMemberData,
  ChangeRoleData,
  AcceptInvitationData,
  TeamInvitation,
  RoleFormData,
} from '@/types/team';

export const teamKeys = {
  all: ['team'] as const,
  members: () => [...teamKeys.all, 'members'] as const,
  invitations: () => [...teamKeys.all, 'invitations'] as const,
  activity: () => [...teamKeys.all, 'activity'] as const,
  organization: () => [...teamKeys.all, 'organization'] as const,
  roles: () => [...teamKeys.all, 'roles'] as const,
  permissionCatalog: () => [...teamKeys.all, 'permission-catalog'] as const,
};

export function useTeamMembers() {
  return useQuery({
    queryKey: teamKeys.members(),
    queryFn: teamApi.getMembers,
  });
}

export function useTeamInvitations() {
  return useQuery({
    queryKey: teamKeys.invitations(),
    queryFn: teamApi.getInvitations,
  });
}

export function useActivityLog() {
  return useQuery({
    queryKey: teamKeys.activity(),
    queryFn: () => teamApi.getActivityLog(),
  });
}

export function useOrganizationSettings() {
  return useQuery({
    queryKey: teamKeys.organization(),
    queryFn: teamApi.getOrganizationSettings,
  });
}

export function useRoles() {
  return useQuery({
    queryKey: teamKeys.roles(),
    queryFn: teamApi.getRoles,
  });
}

export function usePermissionCatalog() {
  return useQuery({
    queryKey: teamKeys.permissionCatalog(),
    queryFn: teamApi.getPermissionCatalog,
    // The vocabulary only changes when the product does.
    staleTime: Infinity,
  });
}

export function useCreateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RoleFormData) => teamApi.createRole(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.roles() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activity() });
      toast.success('Role created');
    },
    onError: (error: any) => {
      toast.error(roleErrorMessage(error, 'Failed to create the role'));
    },
  });
}

export function useUpdateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ roleId, data }: { roleId: string; data: RoleFormData }) =>
      teamApi.updateRole(roleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.roles() });
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activity() });
      // The caller's own access may have just changed.
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      toast.success('Role updated');
    },
    onError: (error: any) => {
      toast.error(roleErrorMessage(error, 'Failed to update the role'));
    },
  });
}

export function useDeleteRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (roleId: string) => teamApi.deleteRole(roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.roles() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activity() });
      toast.success('Role deleted');
    },
    onError: (error: any) => {
      toast.error(roleErrorMessage(error, 'Failed to delete the role'));
    },
  });
}

/**
 * The server's reason, not a generic failure.
 *
 * Refusals here are things the user can act on - a name already taken, a
 * permission they cannot grant, members still holding the role, a plan that
 * does not include custom roles - and a toast saying "failed" hides all of it.
 */
function roleErrorMessage(error: any, fallback: string): string {
  const details = error?.details;
  if (details && typeof details === 'object') {
    const first = Object.values(details)[0];
    if (Array.isArray(first) && first.length) return String(first[0]);
    if (typeof first === 'string') return first;
  }
  return error?.error || error?.message || fallback;
}

export function useInviteMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InviteMemberData) => teamApi.inviteMember(data),
    onSuccess: (invitation: TeamInvitation) => {
      queryClient.invalidateQueries({ queryKey: teamKeys.invitations() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activity() });
      // The invitation is valid either way, so this is not an error — but
      // saying "sent" when it was not is how someone waits a week for an
      // email that never left.
      if (invitation?.email_sent === false) {
        toast.warning(
          'Invitation created, but the email could not be sent. Copy the link and send it yourself.',
          { duration: 8000 }
        );
      } else {
        toast.success('Invitation sent successfully');
      }
    },
    onError: (error: any) => {
      toast.error(error?.error || error?.message || 'Failed to send invitation');
    },
  });
}

export function useResendInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: string) => teamApi.resendInvitation(invitationId),
    onSuccess: (invitation: TeamInvitation) => {
      queryClient.invalidateQueries({ queryKey: teamKeys.invitations() });
      if (invitation?.email_sent === false) {
        toast.warning(
          'Could not send the email. Copy the invitation link and send it yourself.',
          { duration: 8000 }
        );
      } else {
        toast.success('Invitation resent');
      }
    },
    onError: () => {
      toast.error('Failed to resend invitation');
    },
  });
}

export function useCancelInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: string) => teamApi.cancelInvitation(invitationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.invitations() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activity() });
      toast.success('Invitation cancelled');
    },
    onError: () => {
      toast.error('Failed to cancel invitation');
    },
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memberId: string) => teamApi.removeMember(memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activity() });
      toast.success('Member removed successfully');
    },
    onError: (error: any) => {
      toast.error(error?.error || error?.message || 'Failed to remove member');
    },
  });
}

export function useChangeRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memberId, data }: { memberId: string; data: ChangeRoleData }) =>
      teamApi.changeRole(memberId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activity() });
      toast.success('Role updated successfully');
    },
    onError: (error: any) => {
      toast.error(error?.error || error?.message || 'Failed to change role');
    },
  });
}

export function useTransferOwnership() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (newOwnerId: string) => teamApi.transferOwnership(newOwnerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activity() });
      toast.success('Ownership transferred successfully');
    },
    onError: (error: any) => {
      toast.error(error?.error || error?.message || 'Failed to transfer ownership');
    },
  });
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: teamApi.updateOrganizationSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.organization() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activity() });
      toast.success('Organization settings updated');
    },
    onError: () => {
      toast.error('Failed to update organization settings');
    },
  });
}

export function useAcceptInvitation() {
  return useMutation({
    mutationFn: (data: AcceptInvitationData) => teamApi.acceptInvitation(data),
    onError: (error: any) => {
      toast.error(error?.error || error?.message || 'Failed to accept invitation');
    },
  });
}
