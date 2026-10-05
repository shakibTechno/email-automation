/**
 * Types for Contact Segmentation module
 */

// Segment types
export type SegmentType = 'static' | 'dynamic';

// Condition operators by field type
export type StringOperator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'starts_with'
  | 'ends_with'
  | 'is_empty'
  | 'is_not_empty';

export type NumberOperator =
  | 'equals'
  | 'not_equals'
  | 'greater_than'
  | 'less_than'
  | 'greater_or_equal'
  | 'less_or_equal'
  | 'between'
  | 'is_empty'
  | 'is_not_empty';

export type DateOperator =
  | 'equals'
  | 'before'
  | 'after'
  | 'between'
  | 'in_last_days'
  | 'more_than_days_ago'
  | 'is_empty'
  | 'is_not_empty';

export type BooleanOperator = 'is_true' | 'is_false';

export type SelectOperator = 'equals' | 'not_equals' | 'in' | 'not_in';

export type TagOperator =
  | 'has_tag'
  | 'not_has_tag'
  | 'has_any_tag'
  | 'has_all_tags'
  | 'has_no_tags';

export type ConditionOperator =
  | StringOperator
  | NumberOperator
  | DateOperator
  | BooleanOperator
  | SelectOperator
  | TagOperator;

// Field definition from backend
export interface FieldDefinition {
  field: string;
  type: 'string' | 'number' | 'date' | 'boolean' | 'select' | 'tag';
  label: string;
  options?: string[];
  operators: OperatorOption[];
}

export interface OperatorOption {
  value: string;
  label: string;
}

// Condition within rules
export interface SegmentCondition {
  id: string;
  field: string;
  operator: string;
  value: string | number | boolean | string[] | null;
}

// Condition group for nested AND/OR logic
export interface ConditionGroup {
  id: string;
  match_type: 'all' | 'any';
  conditions: SegmentCondition[];
  groups?: ConditionGroup[];
}

// Top-level rules structure
export interface SegmentRules {
  match_type: 'all' | 'any';
  conditions: SegmentCondition[];
  groups?: ConditionGroup[];
}

// Segment model
export interface Segment {
  id: string;
  name: string;
  description: string;
  segment_type: SegmentType;
  rules: SegmentRules;
  contact_count: number;
  last_calculated_at: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  created_by_name: string | null;
}

// Segment list item (lighter)
export interface SegmentListItem {
  id: string;
  name: string;
  description: string;
  segment_type: SegmentType;
  contact_count: number;
  last_calculated_at: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  created_by_name: string | null;
}

// Contact within segment
export interface SegmentContact {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  company: string;
  engagement_level: string;
  is_subscribed: boolean;
  lead_score: number;
  created_at: string;
}

// Segment membership (for static segments)
export interface SegmentMembership {
  id: string;
  contact: string;
  contact_email: string;
  contact_name: string;
  created_at: string;
}

// Tag option for tag field
export interface TagOption {
  id: string;
  name: string;
  color: string;
}

// Preview result
export interface PreviewResult {
  total_count: number;
  sample_contacts: Array<{
    id: string;
    email: string;
    first_name: string | null;
    last_name: string | null;
  }>;
  has_more: boolean;
}

// API request types
export interface CreateSegmentRequest {
  name: string;
  description?: string;
  segment_type: SegmentType;
  rules?: SegmentRules;
}

export interface UpdateSegmentRequest {
  name?: string;
  description?: string;
  rules?: SegmentRules;
}

export interface AddContactsRequest {
  contact_ids: string[];
}

export interface RemoveContactsRequest {
  contact_ids: string[];
}

export interface PreviewRulesRequest {
  rules: SegmentRules;
  limit?: number;
}

// API response types
export interface SegmentListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: SegmentListItem[];
}

export interface SegmentContactsResponse {
  results: SegmentContact[];
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AddContactsResponse {
  added: number;
  already_member: number;
  contact_count: number;
}

export interface RemoveContactsResponse {
  removed: number;
  contact_count: number;
}

export interface RefreshResponse {
  contact_count: number;
  last_calculated_at: string;
}

// Query params
export interface SegmentListParams {
  page?: number;
  page_size?: number;
  search?: string;
  segment_type?: SegmentType;
  ordering?: string;
  min_contacts?: number;
  max_contacts?: number;
}

export interface SegmentContactsParams {
  page?: number;
  page_size?: number;
}
