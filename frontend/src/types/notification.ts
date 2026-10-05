export type NotificationType =
  | 'campaign_sent'
  | 'campaign_failed'
  | 'ab_test_winner_needed'
  | 'ab_test_completed'
  | 'form_submission'
  | 'workflow_failed'
  | 'billing_trial_expiring'
  | 'billing_payment_failed'
  | 'billing_subscription_renewed'
  | 'team_member_joined'
  | 'lead_score_threshold';

export interface Notification {
  id: string;
  notification_type: NotificationType;
  title: string;
  message: string;
  data: Record<string, string>;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface UnreadCountResponse {
  unread_count: number;
}
