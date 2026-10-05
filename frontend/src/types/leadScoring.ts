export type RuleType = 'demographic' | 'behavioral';

export type EventType =
  | 'email_opened'
  | 'email_clicked'
  | 'form_submitted'
  | 'tag_added'
  | 'tag_removed'
  | 'workflow_completed'
  | 'unsubscribed'
  | 'bounced';

export type ConditionOperator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'starts_with'
  | 'ends_with'
  | 'is_empty'
  | 'is_not_empty'
  | 'greater_than'
  | 'less_than'
  | 'greater_or_equal'
  | 'less_or_equal'
  | 'is_true'
  | 'is_false';

export interface RuleCondition {
  field: string;
  operator: ConditionOperator;
  value: string | number;
}

export interface ScoringRule {
  id: string;
  name: string;
  description?: string;
  rule_type: RuleType;
  points: number;
  is_active: boolean;
  priority: number;
  condition: RuleCondition;
  event_type?: EventType;
  event_filter?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ScoringRuleFormData {
  name: string;
  description?: string;
  rule_type: RuleType;
  points: number;
  is_active: boolean;
  priority?: number;
  condition?: Partial<RuleCondition>;
  event_type?: EventType;
  event_filter?: Record<string, string>;
}

export interface ScoreThreshold {
  id: string;
  label: string;
  min_score: number;
  color: string;
  engagement_level: 'high' | 'medium' | 'low' | 'none';
}

export interface ScoreThresholdInput {
  label: string;
  min_score: number;
  color: string;
  engagement_level: 'high' | 'medium' | 'low' | 'none';
}

export interface ScoreHistoryEntry {
  id: string;
  rule?: { id: string; name: string; rule_type: RuleType } | null;
  reason: 'rule' | 'manual' | 'recalculation';
  points_delta: number;
  score_before: number;
  score_after: number;
  note: string;
  created_at: string;
}

export interface ScorePreview {
  current_score: number;
  projected_score: number;
  matched_rules: Array<{ id: string; name: string; points: number }>;
  engagement_level: string;
}

export interface ScoringRuleListParams {
  rule_type?: RuleType;
  is_active?: boolean;
  page?: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
