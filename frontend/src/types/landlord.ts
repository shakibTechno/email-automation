import type { PlanType } from './billing';

/** A tenant as the list shows it — cached metrics only, cheap to assemble. */
export interface TenantRow {
  id: string;
  name: string;
  slug: string;
  plan: PlanType;
  is_active: boolean;
  suspended_at: string | null;
  suspension_reason: string;
  sending_paused: boolean;
  sending_pause_reason: string;
  users: number;
  contacts: number;
  emails_used: number;
  emails_limit: number;
  subscription_status: string | null;
  /** From the mail server's hourly sync; null when no tenant is provisioned. */
  bounce_rate_30d: number | null;
  queued: number;
  held: number;
  mail_status: string | null;
  created_at: string;
}

export interface TenantDetail extends TenantRow {
  email: string;
  deliverability: {
    sent: number;
    bounced: number;
    complained: number;
    bounce_rate: number;
    complaint_rate: number;
  };
  thresholds: { bounce_pct: number | null; complaint_pct: number | null };
  from_identity: { name: string; email: string } | null;
  mail_server: {
    external_id: string;
    status: string;
    suspension_reason: string;
    send_limit_per_hour: number | null;
    sent_last_hour: number;
    last_synced_at: string | null;
  } | null;
  domains: Array<{
    domain: string;
    status: string;
    sending_enabled: boolean;
    verified_at: string | null;
  }>;
  billing: {
    plan: PlanType;
    status: string;
    interval: string;
    trial_end: string | null;
    current_period_end: string | null;
    price: number;
  } | null;
  /** `users` stays the count, as on the row; the people are `members`. */
  members: Array<{
    id: string;
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
    last_login: string | null;
  }>;
  recent_campaigns: Array<{
    id: string;
    name: string;
    status: string;
    recipient_count: number;
    sent_at: string | null;
  }>;
}

/**
 * The list endpoint reads `per_page`, not the `page_size` that the shared
 * PaginationParams type declares. Named for what the API actually accepts so
 * call sites do not have to widen the type inline.
 */
export interface TenantListParams {
  page?: number;
  per_page?: number;
  search?: string;
  plan?: PlanType;
  status?: 'active' | 'suspended';
}

export interface TenantListResponse {
  results: TenantRow[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PlatformOverview {
  period_days: number;
  tenants: { total: number; active: number; suspended: number; new_in_period: number };
  users: number;
  contacts: number;
  campaigns_sent: number;
  emails: {
    sent: number;
    delivered: number;
    bounced: number;
    bounce_rate: number;
  };
  signups_by_day: Array<{ date: string; count: number }>;
  generated_at: string;
}

export interface DeliverabilityRow {
  organization_id: string;
  organization_name: string;
  plan: PlanType;
  is_active: boolean;
  mail_status: string;
  suspension_reason: string;
  bounce_rate_30d: number;
  bounce_threshold: number;
  over_threshold: boolean;
  sending_paused: boolean;
  sent_last_hour: number;
  queued: number;
  held: number;
  unverified_domains: number;
  last_synced_at: string | null;
  /** A blunt ordering, not a measurement — the ranking is the point. */
  risk_score: number;
}

export interface DeliverabilityResponse {
  count: number;
  at_risk: number;
  results: DeliverabilityRow[];
}

export interface RevenueSummary {
  mrr: number;
  by_plan: Array<{ plan: PlanType; count: number; mrr: number }>;
  paying_tenants: number;
  trials_ending: Array<{
    organization_id: string;
    organization_name: string;
    trial_end: string;
    days_left: number;
  }>;
  at_risk: Array<{
    organization_id: string;
    organization_name: string;
    status: string;
    plan: PlanType;
  }>;
  near_quota: Array<{
    organization_id: string;
    organization_name: string;
    used: number;
    limit: number;
    percent: number;
  }>;
}
