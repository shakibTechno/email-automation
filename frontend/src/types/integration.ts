export type AnalyticsProvider = 'google_analytics' | 'facebook_pixel' | 'google_tag_manager';
export type SocialPlatform = 'facebook_lead_ads' | 'linkedin_lead_gen';
export type SocialStatus = 'disconnected' | 'connected' | 'expired' | 'error';
export type SyncLogStatus = 'running' | 'completed' | 'partial' | 'failed';

export interface AnalyticsIntegration {
  id: string;
  provider: AnalyticsProvider;
  tracking_id: string;
  is_enabled: boolean;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface UpsertAnalyticsData {
  provider: AnalyticsProvider;
  tracking_id: string;
  is_enabled?: boolean;
  settings?: Record<string, unknown>;
}

export interface SocialIntegration {
  id: string;
  platform: SocialPlatform;
  status: SocialStatus;
  external_account_id: string;
  external_account_name: string;
  auto_sync: boolean;
  sync_interval_minutes: number;
  last_synced_at: string | null;
  field_mapping: Record<string, string>;
  default_tag: string | null;
  default_tag_name: string | null;
  total_leads_imported: number;
  is_demo: boolean;
  has_credentials: boolean;
  credentials_display: {
    app_id?: string;
    app_secret?: string;
    page_id?: string;
    organization_id?: string;
  };
  connected_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateSocialData {
  auto_sync?: boolean;
  sync_interval_minutes?: number;
  field_mapping?: Record<string, string>;
  default_tag?: string | null;
}

export interface LeadSyncLog {
  id: string;
  status: SyncLogStatus;
  leads_found: number;
  leads_created: number;
  leads_updated: number;
  leads_failed: number;
  error_message: string;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface UpdateCredentialsData {
  app_id: string;
  app_secret: string;
  page_id?: string;
  organization_id?: string;
}

export interface DemoConnectData {
  platform: SocialPlatform;
}

export interface FieldMappingOption {
  value: string;
  label: string;
}
