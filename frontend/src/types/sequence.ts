export interface SequenceStep {
  id: string;
  position: number;
  subject: string;
  template: string | null;
  template_name: string | null;
  delay_days: number;
  delay_hours: number;
  total_delay_hours: number;
}

export interface EmailSequenceListItem {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'paused' | 'archived';
  sender_name: string;
  sender_email: string;
  step_count: number;
  enrolled_count: number;
  completed_count: number;
  allow_reenrollment: boolean;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailSequence extends EmailSequenceListItem {
  reply_to_email: string;
  steps: SequenceStep[];
}

export interface CreateSequenceData {
  name: string;
  description?: string;
  status?: 'draft' | 'active';
  sender_name?: string;
  sender_email?: string;
  reply_to_email?: string;
  allow_reenrollment?: boolean;
}

export interface CreateStepData {
  sequence: string;
  position?: number;
  subject: string;
  template?: string | null;
  delay_days?: number;
  delay_hours?: number;
}

export interface SequenceEnrollment {
  id: string;
  sequence: string;
  sequence_name: string;
  contact: string;
  contact_email: string;
  contact_name: string;
  status: 'active' | 'completed' | 'unsubscribed' | 'paused' | 'cancelled';
  current_step_position: number;
  enrolled_at: string;
  completed_at: string | null;
  next_send_at: string | null;
}

export interface SequenceStepExecution {
  id: string;
  step: string;
  step_subject: string;
  step_position: number;
  status: 'pending' | 'sent' | 'failed' | 'skipped';
  scheduled_at: string;
  sent_at: string | null;
  error_message: string;
  opened_at: string | null;
  clicked_at: string | null;
}

export interface SequenceStats {
  total_enrolled: number;
  active: number;
  completed: number;
  cancelled: number;
  unsubscribed: number;
  completion_rate: number;
  steps: Array<{
    position: number;
    subject: string;
    sent: number;
    opened: number;
    clicked: number;
    open_rate: number;
    click_rate: number;
  }>;
}

export interface ActivityEvent {
  type: string;
  title: string;
  description: string;
  timestamp: string;
  meta: Record<string, unknown>;
}

export interface ActivityTimeline {
  total: number;
  limit: number;
  offset: number;
  events: ActivityEvent[];
}
