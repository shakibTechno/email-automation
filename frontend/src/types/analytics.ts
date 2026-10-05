/**
 * Types for Analytics & Reporting module
 */

// Trend indicator for period-over-period comparison
export interface TrendIndicator {
  value: number;
  change_percent: number;
  direction: 'up' | 'down' | 'flat';
}

// Generic time series data point
export interface TimeSeriesPoint {
  date: string;
  [key: string]: string | number;
}

// Overview
export interface AnalyticsOverview {
  overview: {
    emails_sent: TrendIndicator;
    new_contacts: TrendIndicator;
    form_submissions: TrendIndicator;
    page_views: TrendIndicator;
  };
  trends: TrendPoint[];
}

export interface TrendPoint {
  date: string;
  emails_sent: number;
  new_contacts: number;
  form_submissions: number;
  page_views: number;
}

// Campaign analytics
export interface CampaignMetrics {
  id: string;
  name: string;
  subject: string;
  sent_at: string | null;
  recipient_count: number;
  delivered: number;
  opened: number;
  clicked: number;
  bounced: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
}

export interface CampaignAnalyticsSummary {
  total_sent: number;
  avg_open_rate: number;
  avg_click_rate: number;
  total_bounced: number;
  campaign_count: number;
}

export interface CampaignAnalyticsListResponse {
  summary: CampaignAnalyticsSummary;
  campaigns: CampaignMetrics[];
  top_campaigns: CampaignMetrics[];
}

export interface CampaignStatusBreakdown {
  status: string;
  count: number;
}

export interface CampaignEngagementPoint {
  date: string;
  opens: number;
  clicks: number;
}

export interface CampaignDetailAnalytics {
  campaign: {
    id: string;
    name: string;
    subject: string;
    sent_at: string | null;
  };
  recipient_count: number;
  delivered: number;
  opened: number;
  clicked: number;
  bounced: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
  status_breakdown: CampaignStatusBreakdown[];
  engagement_over_time: CampaignEngagementPoint[];
}

// Contact analytics
export interface EngagementDistribution {
  level: string;
  count: number;
}

export interface SourceDistribution {
  source: string;
  count: number;
}

export interface SubscriptionOverview {
  subscribed: number;
  unsubscribed: number;
  bounced: number;
}

export interface LeadScoreBucket {
  bucket: string;
  count: number;
}

export interface NewVsUnsubscribesPoint {
  date: string;
  new_contacts: number;
  unsubscribes: number;
}

export interface ContactAnalytics {
  total: number;
  new_contacts: TrendIndicator;
  unsubscribes: TrendIndicator;
  growth: TimeSeriesPoint[];
  engagement_distribution: EngagementDistribution[];
  source_distribution: SourceDistribution[];
  subscription_overview: SubscriptionOverview;
  lead_score_distribution: LeadScoreBucket[];
  new_vs_unsubscribes: NewVsUnsubscribesPoint[];
}

// Form analytics
export interface FormMetric {
  id: string;
  name: string;
  status: string;
  submissions: number;
}

export interface TopForm {
  id: string;
  name: string;
  submissions: number;
}

export interface FormAnalytics {
  submissions_over_time: TimeSeriesPoint[];
  top_forms: TopForm[];
  form_metrics: FormMetric[];
}

// Landing page analytics
export interface ViewsPoint {
  date: string;
  total: number;
  unique: number;
}

export interface TopPage {
  id: string;
  name: string;
  views: number;
}

export interface ReferrerBreakdown {
  source: string;
  count: number;
}

export interface DeviceBreakdown {
  device: string;
  count: number;
}

export interface LandingPageAnalytics {
  total_views: number;
  unique_views: number;
  views_over_time: ViewsPoint[];
  top_pages: TopPage[];
  referrer_breakdown: ReferrerBreakdown[];
  device_breakdown: DeviceBreakdown[];
}
