export type UserRole = 'owner' | 'admin' | 'member' | 'viewer';

export interface TeamMember {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

export interface TeamInvitation {
  id: string;
  email: string;
  role: UserRole;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  invited_by_name: string | null;
  expires_at: string;
  created_at: string;
}

export interface InviteMemberData {
  email: string;
  role: 'admin' | 'member' | 'viewer';
}

export interface ChangeRoleData {
  role: 'admin' | 'member' | 'viewer';
}

export interface AcceptInvitationData {
  token: string;
  first_name: string;
  last_name: string;
  password: string;
  password_confirm: string;
}

export interface ActivityLogEntry {
  id: string;
  action: string;
  user_name: string | null;
  target_email: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface OrganizationSettings {
  id: string;
  name: string;
  slug: string;
  domain: string;
  plan: string;
  is_active: boolean;
  email: string;
  phone: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  max_contacts: number;
  max_emails_per_month: number;
  created_at: string;
  updated_at: string;
}

export interface UpdateOrganizationData {
  name?: string;
  domain?: string;
  email?: string;
  phone?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
}
