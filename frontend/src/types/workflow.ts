// Workflow status types
export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'archived';
export type ExecutionStatus = 'active' | 'waiting' | 'completed' | 'failed' | 'cancelled';
export type StepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

/**
 * Node type names.
 *
 * Deliberately `string`, not a union. The server's catalogue is the list, and
 * a hand-written union here is the thing that drifted from it last time: four
 * node types existed server-side and were simply absent from the builder.
 * These aliases stay so existing call sites keep reading as what they are.
 */
export type TriggerNodeType = string;
export type ActionNodeType = string;
export type ConditionNodeType = string;
export type WorkflowNodeType = string;

/** Branch names. A switch node names its own, so this is not exhaustive. */
export type EdgeType = string;

// Node configuration interfaces
export interface TriggerFormSubmissionConfig {
  form_id: string;
  form_name?: string;
}

export interface TriggerTagConfig {
  tag_id: string;
  tag_name?: string;
}

export interface TriggerDateFieldConfig {
  field_name: string;
  offset_days: number;
  time?: string;
}

export interface ActionSendEmailConfig {
  template_id: string;
  template_name?: string;
  subject?: string;
}

export interface ActionTagConfig {
  tag_id: string;
  tag_name?: string;
}

export interface ActionUpdateContactConfig {
  field: string;
  operation: 'set' | 'increment' | 'decrement' | 'append';
  value: string | number;
}

export interface ActionWaitConfig {
  duration: number;
  unit: 'minutes' | 'hours' | 'days';
}

export interface ActionWebhookConfig {
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  payload_template?: string;
}

export interface ConditionRule {
  field: string;
  operator:
    | 'equals'
    | 'not_equals'
    | 'contains'
    | 'not_contains'
    | 'starts_with'
    | 'ends_with'
    | 'is_empty'
    | 'is_not_empty'
    | 'greater_than'
    | 'less_than';
  value: string;
}

export interface ConditionConfig {
  rules: ConditionRule[];
  logic: 'all' | 'any';
}

export type NodeConfig =
  | TriggerFormSubmissionConfig
  | TriggerTagConfig
  | TriggerDateFieldConfig
  | ActionSendEmailConfig
  | ActionTagConfig
  | ActionUpdateContactConfig
  | ActionWaitConfig
  | ActionWebhookConfig
  | ConditionConfig
  | Record<string, unknown>;

// Workflow Node
export interface WorkflowNode {
  id: string;
  node_type: WorkflowNodeType;
  position_x: number;
  position_y: number;
  config: NodeConfig;
  label: string;
  created_at: string;
  updated_at: string;
}

// Workflow Edge
export interface WorkflowEdge {
  id: string;
  source_node: string;
  target_node: string;
  edge_type: EdgeType;
  source_handle: string;
  target_handle: string;
  created_at: string;
}

// Canvas data for React Flow state
export interface CanvasData {
  viewport?: {
    x: number;
    y: number;
    zoom: number;
  };
}

// Workflow
export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  canvas_data: CanvasData;
  goal_node_id: string;
  goal_description: string;
  /** Whether meeting the goal ends the run wherever the contact has got to. */
  exit_on_goal: boolean;
  goal_rules: { rules?: ConditionRule[]; logic?: 'all' | 'any' };
  /** How often one contact may go through: once | one_at_a_time | always. */
  reentry: string;
  reentry_cooldown_days: number;
  entry_segment: string | null;
  respect_quiet_hours: boolean;
  send_window_start: string;
  send_window_end: string;
  /** 0 = Monday .. 6 = Sunday. Empty means every day. */
  send_weekdays: number[];
  /** The path segment for this workflow's inbound URL. Server-minted. */
  webhook_token: string;
  contacts_entered: number;
  contacts_active: number;
  contacts_completed: number;
  contacts_goal_reached: number;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  activated_at: string | null;
  created_by: string;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowListItem {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  contacts_entered: number;
  contacts_active: number;
  contacts_completed: number;
  contacts_goal_reached: number;
  node_count: number;
  activated_at: string | null;
  created_by: string;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

// Workflow Execution Step
export interface WorkflowExecutionStep {
  id: string;
  node: string | null;
  node_type: WorkflowNodeType | null;
  node_label: string | null;
  status: StepStatus;
  started_at: string | null;
  completed_at: string | null;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  branch_taken: string;
  error_message: string;
  created_at: string;
}

// Workflow Execution
export interface WorkflowExecution {
  id: string;
  workflow: string;
  workflow_name: string;
  contact: string;
  contact_email: string;
  contact_name: string;
  status: ExecutionStatus;
  current_node: string | null;
  resume_at: string | null;
  trigger_data: Record<string, unknown>;
  goal_reached: boolean;
  goal_reached_at: string | null;
  started_at: string;
  completed_at: string | null;
  error_message: string;
  retry_count: number;
  steps: WorkflowExecutionStep[];
  created_at: string;
}

export interface WorkflowExecutionListItem {
  id: string;
  contact: string;
  contact_email: string;
  contact_name: string;
  status: ExecutionStatus;
  current_node: string | null;
  current_node_label: string | null;
  goal_reached: boolean;
  goal_reached_at: string | null;
  started_at: string;
  completed_at: string | null;
  step_count: number;
  error_message: string;
  retry_count: number;
}

// Workflow Template
export type TemplateCategory =
  | 'welcome_series'
  | 'lead_nurturing'
  | 're_engagement'
  | 'onboarding'
  | 'promotional'
  | 'custom';

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: TemplateCategory;
  thumbnail_url: string;
  template_data: {
    nodes: Array<{
      id: string;
      node_type: WorkflowNodeType;
      position_x: number;
      position_y: number;
      config: NodeConfig;
      label: string;
    }>;
    edges: Array<{
      source_node_id: string;
      target_node_id: string;
      edge_type: EdgeType;
      source_handle: string;
      target_handle: string;
    }>;
    canvas?: CanvasData;
  };
  is_system: boolean;
  is_active: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTemplateListItem {
  id: string;
  name: string;
  description: string;
  category: TemplateCategory;
  thumbnail_url: string;
  is_system: boolean;
  is_active: boolean;
  usage_count: number;
  created_at: string;
}

// Analytics
export interface WorkflowAnalytics {
  total_entered: number;
  active: number;
  waiting: number;
  completed: number;
  failed: number;
  goal_reached: number;
  period_days: number;
}

// Validation
export interface WorkflowValidation {
  is_valid: boolean;
  errors: string[];
}

// API Request/Response types
export interface WorkflowFilters {
  status?: WorkflowStatus;
  name?: string;
  search?: string;
  ordering?: string;
}

export interface WorkflowExecutionFilters {
  status?: ExecutionStatus;
  goal_reached?: boolean;
  contact?: string;
  ordering?: string;
}

export interface WorkflowTemplateFilters {
  category?: TemplateCategory;
  is_system?: boolean;
  name?: string;
  search?: string;
}

export interface WorkflowListResponse {
  data: WorkflowListItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface WorkflowExecutionListResponse {
  data: WorkflowExecutionListItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface WorkflowTemplateListResponse {
  data: WorkflowTemplateListItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// React Flow node/edge input format
export interface WorkflowNodeInput {
  id: string;
  node_type: WorkflowNodeType;
  position_x: number;
  position_y: number;
  config: NodeConfig;
  label: string;
}

export interface WorkflowEdgeInput {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  type?: EdgeType;
}

export interface CreateWorkflowData {
  name: string;
  description?: string;
  canvas_data?: CanvasData;
  goal_node_id?: string;
  goal_description?: string;
  nodes?: WorkflowNodeInput[];
  edges?: WorkflowEdgeInput[];
}

export interface UpdateWorkflowData {
  name?: string;
  description?: string;
  canvas_data?: CanvasData;
  goal_node_id?: string;
  goal_description?: string;
  nodes?: WorkflowNodeInput[];
  edges?: WorkflowEdgeInput[];
}

/**
 * One node type, as the server describes it.
 *
 * There used to be a hand-written NODE_TYPES array here. It drifted from the
 * backend's own list: four node types worked server-side and were invisible
 * in the builder, so nobody could use them. The catalogue is now served from
 * GET /workflows/node-types/ and this file holds only its shape.
 */
export interface NodeConfigFieldOption {
  value: string;
  label: string;
}

export interface NodeConfigField {
  key: string;
  label: string;
  type: 'text' | 'textarea' | 'number' | 'boolean' | 'select' | 'asset'
    | 'duration' | 'rules';
  asset: string;
  options: NodeConfigFieldOption[];
  required: boolean;
  default: unknown;
  help: string;
  depends_on: { field: string; values: string[] } | null;
}

export interface NodeCatalogEntry {
  type: WorkflowNodeType;
  category: 'trigger' | 'action' | 'condition';
  label: string;
  description: string;
  icon: string;
  /** 'custom' means a hand-written panel owns this node's settings. */
  ui: 'auto' | 'custom';
  terminal: boolean;
  branches: string[];
  config_fields: NodeConfigField[];
}

/** A rule field the executor supports that a segment has no concept of. */
export interface BehaviourRuleField {
  field: string;
  label: string;
  type: string;
  needs_value: boolean;
  value_label?: string;
  value_asset?: string;
}

export interface NodeCatalogResponse {
  nodeTypes: NodeCatalogEntry[];
  ruleFields: {
    behaviour: BehaviourRuleField[];
    behaviour_operators: { value: string; label: string }[];
  };
}

export interface WorkflowImportReport {
  nodes_created: number;
  edges_created: number;
  unresolved: { kind: string; name: string; node: string }[];
  /** Steps that will fail until someone fills them in. */
  needs_attention: string[];
}

