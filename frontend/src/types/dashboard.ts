export interface DashboardOverview {
  contacts: {
    total: number;
  };
  campaigns: {
    total: number;
    sent: number;
  };
  forms: {
    total: number;
    active: number;
  };
  landing_pages: {
    total: number;
    published: number;
  };
}

export interface ContactGrowthData {
  date: string;
  count: number;
}

export interface CampaignStats {
  campaigns_sent: number;
  emails_sent: number;
  emails_delivered: number;
  emails_opened: number;
  emails_clicked: number;
  open_rate: number;
  click_rate: number;
}

export interface FormStats {
  total_submissions: number;
  submissions_by_day: {
    date: string;
    count: number;
  }[];
}

export interface LandingPageStats {
  total_views: number;
  unique_views: number;
  views_by_day: {
    date: string;
    views: number;
    unique_views: number;
  }[];
}

export interface RecentCampaign {
  id: string;
  name: string;
  status: string;
  created_at: string;
  sent_at: string | null;
}

export interface RecentSubmission {
  id: string;
  form_name: string;
  contact_email: string | null;
  created_at: string;
}

export interface TopLandingPage {
  id: string;
  name: string;
  slug: string;
  view_count: number;
  conversion_count: number;
}

export interface DashboardData {
  overview: DashboardOverview;
  contact_growth: ContactGrowthData[];
  campaign_stats: CampaignStats;
  form_stats: FormStats;
  landing_page_stats: LandingPageStats;
  recent_campaigns: RecentCampaign[];
  recent_submissions: RecentSubmission[];
  top_landing_pages: TopLandingPage[];
}
