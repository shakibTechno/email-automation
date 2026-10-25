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

  // Lifecycle. `status`, `bounce_type` and `complained_at` are derived by the
  // server from the subscription flags and are read-only here — an editable
  // copy would be a second definition of the same fact.
  status?: 'active' | 'unsubscribed' | 'bounced' | 'complained';
  bounce_type?: 'soft' | 'hard' | '';
  complained_at?: string | null;
  lifecycle_stage?: 'subscriber' | 'lead' | 'qualified' | 'customer' | 'evangelist';

  // Personal
  salutation?: string;
  middle_name?: string;
  preferred_name?: string;
  date_of_birth?: string | null;
  mobile_phone?: string;
  website?: string;
  linkedin_url?: string;

  // Address and locale
  address_line1?: string;
  address_line2?: string;
  city?: string;
  region?: string;
  postal_code?: string;
  /** ISO-3166 alpha-2. */
  country?: string;
  /** IANA name, e.g. Europe/London. */
  timezone?: string;
  /** BCP-47 tag, e.g. en-GB. */
  locale?: string;

  // Consent provenance — what has to be produced if consent is challenged.
  consent_at?: string | null;
  consent_source?: string;
  opt_in_ip?: string | null;
  double_opt_in_at?: string | null;
  /** Identifier in an upstream system, making integration sync idempotent. */
  external_id?: string;

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

export type CustomFieldType =
  | 'text'
  | 'number'
  | 'date'
  | 'boolean'
  | 'dropdown'
  | 'multiselect'
  | 'url'
  | 'email';

/**
 * A contact custom field definition.
 *
 * The field names here match what the API actually returns. They did not
 * before — this said `options` and `required` where the API sends
 * `dropdown_options` and `is_required`, so nothing that read them worked.
 */
export interface CustomField {
  id: string;
  /** The immutable JSON key values are stored under. Read-only. */
  key: string;
  /** The label people see. Safe to rename; the key does not change. */
  name: string;
  field_type: CustomFieldType;
  is_required: boolean;
  default_value?: string;
  dropdown_options: string[];
  help_text?: string;
  display_order: number;
  /** How many contacts hold a value — shown before deleting one. */
  contact_count: number;
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
