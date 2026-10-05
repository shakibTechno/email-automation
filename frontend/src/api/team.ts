import apiClient from './client';
import type {
  TeamMember,
  TeamInvitation,
  InviteMemberData,
  ChangeRoleData,
  AcceptInvitationData,
  ActivityLogEntry,
  OrganizationSettings,
  UpdateOrganizationData,
} from '@/types/team';
import type { AuthResponse } from '@/types/auth';

const BASE_URL = '/team';

// Members
export async function getMembers(): Promise<TeamMember[]> {
  const response = await apiClient.get<TeamMember[]>(`${BASE_URL}/members`);
  return response.data;
}

export async function removeMember(memberId: string): Promise<void> {
  await apiClient.delete(`${BASE_URL}/members/${memberId}`);
}

export async function changeRole(memberId: string, data: ChangeRoleData): Promise<TeamMember> {
  const response = await apiClient.patch<TeamMember>(`${BASE_URL}/members/${memberId}/role`, data);
  return response.data;
}

export async function transferOwnership(newOwnerId: string): Promise<{ message: string; new_owner: TeamMember }> {
  const response = await apiClient.post(`${BASE_URL}/transfer-ownership`, { new_owner_id: newOwnerId });
  return response.data;
}

// Invitations
export async function getInvitations(): Promise<TeamInvitation[]> {
  const response = await apiClient.get<TeamInvitation[]>(`${BASE_URL}/invitations`);
  return response.data;
}

export async function inviteMember(data: InviteMemberData): Promise<TeamInvitation> {
  const response = await apiClient.post<TeamInvitation>(`${BASE_URL}/invite`, data);
  return response.data;
}

export async function resendInvitation(invitationId: string): Promise<TeamInvitation> {
  const response = await apiClient.post<TeamInvitation>(`${BASE_URL}/invitations/${invitationId}/resend`);
  return response.data;
}

export async function cancelInvitation(invitationId: string): Promise<void> {
  await apiClient.delete(`${BASE_URL}/invitations/${invitationId}`);
}

// Accept invitation (public)
export async function acceptInvitation(data: AcceptInvitationData): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>(`${BASE_URL}/accept-invitation`, data);
  return response.data;
}

// Activity
export async function getActivityLog(limit: number = 50): Promise<ActivityLogEntry[]> {
  const response = await apiClient.get<ActivityLogEntry[]>(`${BASE_URL}/activity`, {
    params: { limit },
  });
  return response.data;
}

// Organization
export async function getOrganizationSettings(): Promise<OrganizationSettings> {
  const response = await apiClient.get<OrganizationSettings>(`${BASE_URL}/organization`);
  return response.data;
}

export async function updateOrganizationSettings(data: UpdateOrganizationData): Promise<OrganizationSettings> {
  const response = await apiClient.patch<OrganizationSettings>(`${BASE_URL}/organization`, data);
  return response.data;
}
