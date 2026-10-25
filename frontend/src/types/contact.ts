export interface Contact {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  phone?: string;
  company?: string;
  job_title?: string;
  lead_score: number;
  engagement_level: 'low' | 'medium' | 'high' | 'none';
  is_subscribed: boolean;
  is_verified?: boolean;
  unsubscribed_at?: string;
  bounced_at?: string;
  source?: string;
  last_activity_at?: string;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  tags?: Tag[];
  tag_details?: Tag[];
  custom_fields?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: string;
  name: string;
  color: string;
  description?: string;
  /** Contacts currently carrying this tag, annotated by the tags endpoint. */
  contact_count?: number;
  created_at: string;
  updated_at: string;
}

export interface CustomField {
  id: string;
  name: string;
  field_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  options?: string[];
  required: boolean;
  organization_id: string;
  created_at: string;
  updated_at: string;
}

export interface CreateContactData {
  email: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  company?: string;
  job_title?: string;
  subscription_status?: 'active' | 'unsubscribed' | 'bounced' | 'complained';
  assigned_to?: string | null;
  tag_ids?: string[];
  custom_fields?: Record<string, any>;
}

export interface UpdateContactData extends Partial<CreateContactData> {}

export interface ContactFilters {
  search?: string;
  subscription_status?: string[];
  engagement_level?: string[];
  tag_ids?: string[];
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ContactListResponse {
  data: Contact[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export type TimelineEventType =
  | 'email_sent' | 'email_opened' | 'email_clicked' | 'email_bounced' | 'email_unsubscribed'
  | 'form_submission'
  | 'workflow_started' | 'workflow_completed'
  | 'score_change'
  | `crm_${string}`;

export interface TimelineEvent {
  id: string;
  type: TimelineEventType;
  title: string;
  description: string;
  timestamp: string | null;
  metadata: Record<string, any>;
}

export interface TimelineResponse {
  count: number;
  results: TimelineEvent[];
}

export interface DuplicateGroup {
  email: string;
  count: number;
  contacts: Contact[];
}

export interface DuplicatesResponse {
  duplicate_groups: DuplicateGroup[];
  total_groups: number;
}

export interface BulkActionData {
  contact_ids: string[];
  action: 'delete' | 'add_tags' | 'remove_tags' | 'update_status';
  tag_ids?: string[];
  status?: string;
}

export interface ImportContactData {
  file: File;
  field_mapping: Record<string, string>;
  skip_duplicates: boolean;
}

export interface CreateTagData {
  name: string;
  color: string;
  description?: string;
}

export interface UpdateTagData extends Partial<CreateTagData> {}
