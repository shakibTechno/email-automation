export type CampaignStatus = 'draft' | 'scheduled' | 'sending' | 'sent' | 'paused' | 'cancelled' | 'archived';
export type RecipientType = 'all_subscribed' | 'by_tags';
export type ABTestType = 'subject' | 'sender_name' | 'content';
export type ABTestWinnerCriteria = 'open_rate' | 'click_rate';
export type ABTestWinnerSelection = 'auto' | 'manual';
export type ABTestStatus = 'draft' | 'testing' | 'winner_declared' | 'completed';

export interface SendProgress {
  sent: number;
  total: number;
  percent: number;
}

export interface ABTestVariant {
  id: string;
  variant: 'a' | 'b';
  subject: string;
  sender_name: string;
  template: string | null;
  template_name: string | null;
  recipient_count: number;
  sent_count: number;
  open_count: number;
  click_count: number;
  open_rate: number;
  click_rate: number;
}

export interface ABTest {
  id: string;
  test_type: ABTestType;
  test_percentage: number;
  winner_criteria: ABTestWinnerCriteria;
  winner_selection: ABTestWinnerSelection;
  test_duration_hours: number;
  winner_variant: 'a' | 'b' | null;
  status: ABTestStatus;
  winner_sent_at: string | null;
  variants: ABTestVariant[];
  created_at: string;
  updated_at: string;
}

export interface ABTestConfig {
  test_type: ABTestType;
  test_percentage: number;
  winner_criteria: ABTestWinnerCriteria;
  winner_selection: ABTestWinnerSelection;
  test_duration_hours: number;
  variant_b_subject?: string;
  variant_b_sender_name?: string;
  variant_b_template?: string | null;
}

export interface Campaign {
  id: string;
  name: string;
  status: CampaignStatus;
  subject: string;
  preheader_text?: string;
  sender_name: string;
  sender_email: string;
  reply_to_email?: string;
  template?: string;
  template_name?: string;
  template_data?: {
    id: string;
    name: string;
    category: string;
    thumbnail_url?: string;
  };
  recipient_type: RecipientType;
  recipient_tags_detail?: { id: string; name: string; color: string }[];
  recipient_count: number;
  scheduled_at?: string;
  sent_at?: string;
  completed_at?: string;
  created_by?: string;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
  send_progress?: SendProgress | null;
  ab_test?: ABTest | null;
}

export interface CreateCampaignData {
  name: string;
  subject?: string;
  preheader_text?: string;
  sender_name?: string;
  sender_email?: string;
  reply_to_email?: string;
  template?: string;
  recipient_type?: RecipientType;
  recipient_tag_ids?: string[];
  scheduled_at?: string;
}

export interface UpdateCampaignData extends Partial<CreateCampaignData> {}

export interface CampaignFilters {
  search?: string;
  status?: CampaignStatus;
  created_after?: string;
  created_before?: string;
}

export interface CampaignListResponse {
  data: Campaign[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface CampaignSendData {
  send_now: boolean;
  scheduled_at?: string;
}

export interface CampaignTestEmailData {
  test_emails: string[];
}

export type RecipientStatus =
  | 'pending'
  | 'sent'
  | 'delivered'
  | 'opened'
  | 'clicked'
  | 'bounced'
  | 'complained'
  | 'unsubscribed'
  | 'failed';

export interface CampaignRecipient {
  id: string;
  email: string;
  contact_name?: string;
  status: RecipientStatus;
  sent_at?: string;
  opened_at?: string;
  clicked_at?: string;
}
