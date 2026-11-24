/** The four roles every organization has. */
export type BuiltInRole = 'owner' | 'admin' | 'member' | 'viewer';

/**
 * A role slug: one of the built-ins, or one the organization defined.
 *
 * Not a closed union any more - the set is per organization and lives in the
 * database, so anything that needs a label reads `role_name` instead of
 * mapping the slug.
 */
export type UserRole = string;

/** A role the organization defined for itself. */
export interface Role {
  id: string;
  name: string;
  slug: string;
  permissions: string[];
  member_count: number;
  created_at: string;
}

export interface RoleFormData {
  name?: string;
  permissions?: string[];
}

/** One permission a resource can grant, e.g. `campaigns.send`. */
export interface PermissionVerb {
  key: string;
  label: string;
  code: string;
}

export interface PermissionResource {
  key: string;
  label: string;
  group: string;
  verbs: PermissionVerb[];
}

export interface RolePreset {
  slug: BuiltInRole;
  name: string;
  permissions: string[];
  assignable: boolean;
}

/**
 * The permission vocabulary, served by the API rather than declared here.
 *
 * The matrix the settings screen draws has to be the matrix the backend
 * enforces; two copies of it would drift the first time a resource is added.
 */
export interface PermissionCatalog {
  resources: PermissionResource[];
  presets: RolePreset[];
}

export interface TeamMember {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: UserRole;
  /** The role's display name - a built-in label or the organization's own. */
  role_name: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

export interface TeamInvitation {
  id: string;
  email: string;
  role: UserRole;
  role_name: string;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  invited_by_name: string | null;
  /** False when the invitation exists but the email could not be sent. */
  email_sent: boolean;
  email_sent_at: string | null;
  email_error: string;
  /** The link to pass on by hand; null once the invitation is spent. */
  accept_url: string | null;
  expires_at: string;
  created_at: string;
}

export interface InviteMemberData {
  email: string;
  role: UserRole;
}

export interface ChangeRoleData {
  role: UserRole;
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
