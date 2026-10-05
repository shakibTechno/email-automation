/**
 * Types for the CRM & Pipeline module
 */

export type DealStatus = 'open' | 'won' | 'lost';
export type DealPriority = 'low' | 'medium' | 'high';
export type StageType = 'open' | 'won' | 'lost';
export type ActivityType = 'call' | 'email' | 'meeting' | 'task' | 'note';
export type DealContactRole = 'primary' | 'decision_maker' | 'influencer' | 'champion' | 'other';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';
export type TaskStatus = 'todo' | 'in_progress' | 'done';
export type CompanyIndustry =
  | 'technology' | 'financial_services' | 'healthcare' | 'retail'
  | 'manufacturing' | 'real_estate' | 'education' | 'media'
  | 'consulting' | 'other';
export type CompanySize = '1-10' | '11-50' | '51-200' | '201-500' | '501-1000' | '1001+';

// Stage
export interface Stage {
  id: string;
  name: string;
  color: string;
  position: number;
  stage_type: StageType;
  default_probability: number;
  created_at: string;
}

// Pipeline
export interface PipelineListItem {
  id: string;
  name: string;
  description: string;
  is_default: boolean;
  total_deals: number;
  total_value: number;
  stage_count: number;
  created_at: string;
}

export interface Pipeline extends PipelineListItem {
  stages: Stage[];
  created_by: string | null;
  updated_at: string;
}

// Deal
export interface DealListItem {
  id: string;
  title: string;
  status: DealStatus;
  value: number;
  currency: string;
  probability: number;
  weighted_value: number;
  stage: string;
  stage_name: string;
  stage_color: string;
  primary_contact: string | null;
  primary_contact_name: string | null;
  primary_contact_email: string | null;
  priority: DealPriority;
  close_date: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
  company: string | null;
  company_name: string | null;
  is_rotting: boolean;
  last_activity_at: string | null;
  created_at: string;
}

export interface DealKanbanCard {
  id: string;
  title: string;
  value: number;
  currency: string;
  probability: number;
  status: DealStatus;
  primary_contact_name: string | null;
  primary_contact_email: string | null;
  priority: DealPriority;
  close_date: string | null;
  position: number;
  activity_count: number;
  is_rotting: boolean;
  last_activity_at: string | null;
  days_since_activity: number | null;
}

export interface DealContactItem {
  id: string;
  contact: string;
  contact_name: string;
  contact_email: string;
  role: DealContactRole;
  is_primary: boolean;
  created_at: string;
}

export interface DealStageHistoryItem {
  id: string;
  from_stage_name: string | null;
  to_stage_name: string | null;
  moved_by_name: string | null;
  created_at: string;
}

export interface Deal {
  id: string;
  title: string;
  description: string;
  status: DealStatus;
  priority: DealPriority;
  value: number;
  currency: string;
  probability: number;
  weighted_value: number;
  close_date: string | null;
  closed_at: string | null;
  win_reason: string;
  loss_reason: string;
  position: number;
  pipeline: string;
  pipeline_name: string;
  stage: string;
  stage_name: string;
  stage_color: string;
  primary_contact: string | null;
  primary_contact_name: string | null;
  primary_contact_email: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
  created_by: string | null;
  created_by_name: string | null;
  company: string | null;
  company_name: string | null;
  contacts: DealContactItem[];
  stage_history: DealStageHistoryItem[];
  recent_activities: ActivityListItem[];
  activity_count: number;
  stages: Stage[];
  is_rotting: boolean;
  last_activity_at: string | null;
  rotting_threshold_days: number;
  created_at: string;
  updated_at: string;
}

// Kanban
export interface KanbanStage {
  stage: Stage;
  deals: DealKanbanCard[];
  deal_count: number;
  total_value: number;
}

// Activity
export interface ActivityListItem {
  id: string;
  activity_type: ActivityType;
  title: string;
  description: string;
  due_date: string | null;
  is_completed: boolean;
  completed_at: string | null;
  duration: number | null;
  deal: string | null;
  deal_title: string | null;
  contact: string | null;
  contact_name: string | null;
  created_by_name: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
  created_at: string;
}

export interface Activity extends ActivityListItem {
  created_by: string | null;
  updated_at: string;
}

// Pipeline Analytics
export interface StageValue {
  stage_id: string;
  stage_name: string;
  stage_color: string;
  total_value: number;
  deal_count: number;
}

export interface ConversionRate {
  stage_id: string;
  stage_name: string;
  entered: number;
  progressed: number;
  conversion_rate: number;
}

export interface PipelineSummary {
  open_deals_count: number;
  open_deals_value: number;
  won_deals_count: number;
  won_deals_value: number;
  win_rate: number;
  avg_deal_size: number;
}

export interface PipelineAnalytics {
  value_by_stage: StageValue[];
  win_rate: number;
  avg_deal_size: number;
  conversion_rates: ConversionRate[];
  summary: PipelineSummary;
}

// Create/Update types
export interface CreatePipelineData {
  name: string;
  description?: string;
  stages?: {
    name: string;
    color?: string;
    stage_type?: StageType;
    default_probability?: number;
  }[];
}

export interface UpdatePipelineData {
  name?: string;
  description?: string;
}

export interface CreateDealData {
  title: string;
  description?: string;
  pipeline: string;
  stage?: string;
  value?: number;
  currency?: string;
  probability?: number;
  priority?: DealPriority;
  close_date?: string | null;
  primary_contact?: string | null;
  assigned_to?: string | null;
  contact_ids?: string[];
}

export interface UpdateDealData {
  title?: string;
  description?: string;
  value?: number;
  currency?: string;
  probability?: number;
  priority?: DealPriority;
  close_date?: string | null;
  primary_contact?: string | null;
  assigned_to?: string | null;
}

export interface CreateActivityData {
  activity_type: ActivityType;
  title: string;
  description?: string;
  deal?: string | null;
  contact?: string | null;
  due_date?: string | null;
  duration?: number | null;
  assigned_to?: string | null;
}

export interface UpdateActivityData {
  activity_type?: ActivityType;
  title?: string;
  description?: string;
  due_date?: string | null;
  duration?: number | null;
  assigned_to?: string | null;
}

// Filters
export interface DealFilters {
  status?: DealStatus;
  pipeline?: string;
  stage?: string;
  assigned_to?: string;
  priority?: DealPriority;
  close_date_after?: string;
  close_date_before?: string;
  min_value?: number;
  max_value?: number;
  primary_contact?: string;
  search?: string;
}

export interface ActivityFilters {
  activity_type?: ActivityType;
  deal?: string;
  contact?: string;
  is_completed?: boolean;
  due_after?: string;
  due_before?: string;
  assigned_to?: string;
  search?: string;
}

// CRM Tasks
export interface CRMTaskListItem {
  id: string;
  title: string;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string | null;
  completed_at: string | null;
  deal: string | null;
  deal_title: string | null;
  contact: string | null;
  contact_name: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
  is_overdue: boolean;
  created_at: string;
}

export interface CRMTask extends CRMTaskListItem {
  description: string;
  created_by: string | null;
  created_by_name: string | null;
  updated_at: string;
}

export interface CreateTaskData {
  title: string;
  description?: string;
  priority?: TaskPriority;
  status?: TaskStatus;
  due_date?: string | null;
  deal?: string | null;
  contact?: string | null;
  assigned_to?: string | null;
}

export interface UpdateTaskData {
  title?: string;
  description?: string;
  priority?: TaskPriority;
  status?: TaskStatus;
  due_date?: string | null;
  assigned_to?: string | null;
}

export interface TaskFilters {
  status?: TaskStatus;
  priority?: TaskPriority;
  deal?: string;
  contact?: string;
  assigned_to?: string;
  is_overdue?: boolean;
  search?: string;
}

// Revenue Forecasting
export interface ForecastBucket {
  month: string | null;
  label: string;
  weighted: number;
  best_case: number;
  deal_count: number;
}

export interface ForecastData {
  buckets: ForecastBucket[];
  total_weighted: number;
  total_best_case: number;
  open_deals_count: number;
  rotting_deals_count: number;
}

// Companies
export interface CompanyListItem {
  id: string;
  name: string;
  website: string;
  domain: string;
  industry: CompanyIndustry | '';
  size: CompanySize | '';
  phone: string;
  owner: string | null;
  owner_name: string | null;
  contact_count: number;
  deal_count: number;
  open_deal_value: number;
  created_at: string;
}

export interface Company extends CompanyListItem {
  annual_revenue: number | null;
  address: string;
  description: string;
  updated_at: string;
}

export interface CreateCompanyData {
  name: string;
  website?: string;
  domain?: string;
  industry?: CompanyIndustry | '';
  size?: CompanySize | '';
  annual_revenue?: number | null;
  phone?: string;
  address?: string;
  description?: string;
  owner?: string | null;
}

export interface UpdateCompanyData extends Partial<CreateCompanyData> {}

export interface CompanyFilters {
  industry?: CompanyIndustry;
  size?: CompanySize;
  owner?: string;
  search?: string;
}

// List responses
export interface DealListResponse {
  data: DealListItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ActivityListResponse {
  data: ActivityListItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
