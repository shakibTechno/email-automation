// Workflow status types
export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'archived';
export type ExecutionStatus = 'active' | 'waiting' | 'completed' | 'failed' | 'cancelled';
export type StepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

// Node types
export type TriggerNodeType =
  | 'trigger_form_submission'
  | 'trigger_tag_added'
  | 'trigger_tag_removed'
  | 'trigger_contact_created'
  | 'trigger_email_opened'
  | 'trigger_email_clicked'
  | 'trigger_date_field'
  | 'trigger_deal_stage_changed'
  | 'trigger_deal_created';

export type ActionNodeType =
  | 'action_send_email'
  | 'action_add_tag'
  | 'action_remove_tag'
  | 'action_update_contact'
  | 'action_wait'
  | 'action_webhook'
  | 'action_goal'
  | 'action_update_deal';

export type ConditionNodeType = 'condition_if_else';

export type WorkflowNodeType = TriggerNodeType | ActionNodeType | ConditionNodeType;

export type EdgeType = 'default' | 'true' | 'false';

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

// Node type metadata for UI
export interface NodeTypeInfo {
  type: WorkflowNodeType;
  category: 'trigger' | 'action' | 'condition';
  label: string;
  description: string;
  icon: string;
  color: string;
}

export const NODE_TYPES: NodeTypeInfo[] = [
  // Triggers
  {
    type: 'trigger_form_submission',
    category: 'trigger',
    label: 'Form Submission',
    description: 'When a form is submitted',
    icon: 'FileText',
    color: '#3b82f6',
  },
  {
    type: 'trigger_tag_added',
    category: 'trigger',
    label: 'Tag Added',
    description: 'When a tag is added to a contact',
    icon: 'Tag',
    color: '#3b82f6',
  },
  {
    type: 'trigger_tag_removed',
    category: 'trigger',
    label: 'Tag Removed',
    description: 'When a tag is removed from a contact',
    icon: 'TagOff',
    color: '#3b82f6',
  },
  {
    type: 'trigger_contact_created',
    category: 'trigger',
    label: 'Contact Created',
    description: 'When a new contact is created',
    icon: 'UserPlus',
    color: '#3b82f6',
  },
  {
    type: 'trigger_email_opened',
    category: 'trigger',
    label: 'Email Opened',
    description: 'When an email is opened',
    icon: 'MailOpen',
    color: '#3b82f6',
  },
  {
    type: 'trigger_email_clicked',
    category: 'trigger',
    label: 'Email Clicked',
    description: 'When a link in an email is clicked',
    icon: 'MousePointerClick',
    color: '#3b82f6',
  },
  {
    type: 'trigger_date_field',
    category: 'trigger',
    label: 'Date Field',
    description: 'Trigger on a specific date (birthday, anniversary)',
    icon: 'Calendar',
    color: '#3b82f6',
  },
  {
    type: 'trigger_deal_stage_changed',
    category: 'trigger',
    label: 'Deal Stage Changed',
    description: 'When a deal moves to a new pipeline stage',
    icon: 'Briefcase',
    color: '#3b82f6',
  },
  {
    type: 'trigger_deal_created',
    category: 'trigger',
    label: 'Deal Created',
    description: 'When a new deal is created',
    icon: 'PlusSquare',
    color: '#3b82f6',
  },
  // Actions
  {
    type: 'action_send_email',
    category: 'action',
    label: 'Send Email',
    description: 'Send an email to the contact',
    icon: 'Mail',
    color: '#22c55e',
  },
  {
    type: 'action_add_tag',
    category: 'action',
    label: 'Add Tag',
    description: 'Add a tag to the contact',
    icon: 'TagPlus',
    color: '#22c55e',
  },
  {
    type: 'action_remove_tag',
    category: 'action',
    label: 'Remove Tag',
    description: 'Remove a tag from the contact',
    icon: 'TagMinus',
    color: '#22c55e',
  },
  {
    type: 'action_update_contact',
    category: 'action',
    label: 'Update Contact',
    description: 'Update a contact field',
    icon: 'UserCog',
    color: '#22c55e',
  },
  {
    type: 'action_wait',
    category: 'action',
    label: 'Wait',
    description: 'Wait for a specified duration',
    icon: 'Clock',
    color: '#22c55e',
  },
  {
    type: 'action_webhook',
    category: 'action',
    label: 'Webhook',
    description: 'Send data to an external URL',
    icon: 'Webhook',
    color: '#22c55e',
  },
  {
    type: 'action_goal',
    category: 'action',
    label: 'Goal',
    description: 'Mark workflow goal as reached',
    icon: 'Target',
    color: '#8b5cf6',
  },
  {
    type: 'action_update_deal',
    category: 'action',
    label: 'Update Deal',
    description: 'Update a field on the deal that triggered this workflow',
    icon: 'Briefcase',
    color: '#22c55e',
  },
  // Conditions
  {
    type: 'condition_if_else',
    category: 'condition',
    label: 'If/Else',
    description: 'Branch based on conditions',
    icon: 'GitBranch',
    color: '#f59e0b',
  },
];

export const getNodeTypeInfo = (type: WorkflowNodeType): NodeTypeInfo | undefined => {
  return NODE_TYPES.find((n) => n.type === type);
};
