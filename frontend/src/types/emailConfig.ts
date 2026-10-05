export type EmailProvider =
  | 'platform_default'
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

export interface SendingDomain {
  id: string;
  domain: string;
  status: DomainStatus;
  verified_at: string | null;
  spf_record: string;
  dkim_selector: string;
  dkim_record_name: string;
  dkim_record_value: string;
  last_check_at: string | null;
  last_check_error: string;
  created_at: string;
}
