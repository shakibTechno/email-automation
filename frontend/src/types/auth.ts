export interface Organization {
  id: string;
  name: string;
  slug?: string;
  email?: string;
  plan?: 'free' | 'starter' | 'professional' | 'business' | 'enterprise';
  created_at: string;
  updated_at: string;
  /** Identifies this organization to the website snippet. Public by design —
   *  it ships in the page source of the customer's own site. */
  tracking_key?: string;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  /**
   * Null for platform staff, who belong to no tenant and use the landlord
   * console. The API has always been able to return null here; declaring it
   * non-nullable made that a type lie rather than preventing it.
   */
  organization: Organization | null;
  /** Organization-scoped. Says nothing about platform access — see is_staff. */
  role: 'owner' | 'admin' | 'member' | 'viewer';
  /** Platform operator. The only thing that grants the landlord console. */
  is_staff?: boolean;
  is_active?: boolean;
  is_email_verified?: boolean;
  phone?: string;
  avatar?: string;
  timezone?: string;
  language?: string;
  /** Default reply-to for campaigns and sequences this user creates. Blank
   *  means the organization's address applies. */
  reply_to_email?: string;
  created_at: string;
  updated_at: string;
  last_login?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  organization_name: string;
}

export interface AuthResponse {
  user: User;
  tokens: {
    access: string;
    refresh: string;
  };
  message: string;
}

export interface ForgotPasswordData {
  email: string;
}

/**
 * Mirrors what `/auth/password-reset/confirm/` actually reads. This previously
 * declared `password` / `password_confirmation`, which the endpoint has never
 * accepted -- the same mismatch as ChangePasswordData below, and invisible for
 * the same reason: nothing ever called it.
 */
export interface ResetPasswordData {
  token: string;
  new_password: string;
  new_password_confirm: string;
}

/**
 * Mirrors what `/auth/change-password/` actually reads. The form fields are
 * named `current_password` and `new_password_confirmation`, so the submit
 * handler maps them — the previous shape silently sent neither key the API
 * looks for, and every attempt failed validation.
 */
export interface ChangePasswordData {
  old_password: string;
  new_password: string;
  new_password_confirm: string;
}

export interface UpdateProfileData {
  first_name?: string;
  last_name?: string;
  email?: string;
  reply_to_email?: string;
}
