export type EmailProvider =
  | 'platform_default'
  | 'postal'
  | 'smtp'
  | 'sendgrid'
  | 'mailgun'
  | 'ses';

export interface EmailConfig {
  id: string;
  // Identity
  from_name: string;
  from_email: string;
  reply_to_email: string;
  // Provider
  provider: EmailProvider;
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password_set: boolean;
  smtp_use_tls: boolean;
  smtp_use_ssl: boolean;
  api_key_set: boolean;
  provider_domain: string;
  provider_region: string;
  // Compliance
  physical_address: string;
  email_footer_text: string;
  unsubscribe_redirect_url: string;
  // Limits
  daily_send_limit: number;
  hourly_send_limit: number;
  // Thresholds
  bounce_threshold_pct: string;
  complaint_threshold_pct: string;
  sending_paused_due_to_threshold: boolean;
  updated_at: string;
}

export interface UpdateEmailConfigData {
  from_name?: string;
  from_email?: string;
  reply_to_email?: string;
  provider?: EmailProvider;
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_password?: string;
  smtp_use_tls?: boolean;
  smtp_use_ssl?: boolean;
  api_key?: string;
  provider_domain?: string;
  provider_region?: string;
  physical_address?: string;
  email_footer_text?: string;
  unsubscribe_redirect_url?: string;
  daily_send_limit?: number;
  hourly_send_limit?: number;
  bounce_threshold_pct?: string;
  complaint_threshold_pct?: string;
}

export type DomainStatus = 'pending' | 'verified' | 'failed';

/** What each DNS record check came back as. 'Unchecked' means not yet looked up. */
export type DnsRecordStatus = 'OK' | 'Missing' | 'Invalid' | 'Unchecked' | string;

/**
 * One DNS record the customer must publish, as returned by the mail server.
 * There are four — SPF, DKIM, return path and DMARC — and sending is enabled
 * only once every one of them passes.
 */
export interface DnsRecord {
  purpose: 'spf' | 'dkim' | 'return_path' | 'dmarc';
  type: 'TXT' | 'CNAME' | string;
  host: string;
  value: string;
  status: DnsRecordStatus;
  error: string | null;
  /** Guidance for this specific record, e.g. the one-SPF-record-per-domain trap. */
  note: string;
}

export interface SendingDomain {
  id: string;
  domain: string;
  status: DomainStatus;
  verified_at: string | null;
  /** The records to publish, with a per-record check result. */
  dns_records: DnsRecord[];
  /** The mail server's verdict: true only when all four records pass. */
  sending_enabled: boolean;
  last_check_at: string | null;
  last_check_error: string;
  created_at: string;
}

export type PostalTenantStatus = 'active' | 'suspended' | 'error';

/** The organization's own mail server, created on the first sending domain. */
export interface PostalTenant {
  id: string;
  external_id: string;
  status: PostalTenantStatus;
  suspension_reason: string;
  api_key_set: boolean;
  send_limit_per_hour: number | null;
  ip_pool: string;
  sent_last_hour: number;
  queued: number;
  held: number;
  bounce_rate_30d: string;
  last_synced_at: string | null;
  last_error: string;
  created_at: string;
}
