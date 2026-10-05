export type LandingPageStatus = 'draft' | 'published';

export type TemplateCategory =
  | 'lead_generation'
  | 'webinar'
  | 'ebook'
  | 'product_launch'
  | 'event'
  | 'coming_soon'
  | 'thank_you'
  | 'blank';

export const templateCategoryLabels: Record<TemplateCategory, string> = {
  lead_generation: 'Lead Generation',
  webinar: 'Webinar Registration',
  ebook: 'E-book Download',
  product_launch: 'Product Launch',
  event: 'Event Registration',
  coming_soon: 'Coming Soon',
  thank_you: 'Thank You',
  blank: 'Blank',
};

export interface LandingPage {
  id: string;
  name: string;
  slug: string;
  status: LandingPageStatus;
  html_content?: string;
  design_json?: Record<string, any>;
  css_content?: string;
  // SEO
  seo_title?: string;
  seo_description?: string;
  seo_keywords?: string;
  og_image?: string;
  // Settings
  favicon?: string;
  google_analytics_id?: string;
  facebook_pixel_id?: string;
  custom_head_code?: string;
  custom_body_code?: string;
  // Form
  form?: string | null;
  form_name?: string | null;
  // Analytics
  view_count: number;
  conversion_count: number;
  conversion_rate: number;
  // Metadata
  public_url?: string;
  published_at?: string;
  created_by?: string;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateLandingPageData {
  name: string;
  slug?: string;
  template_id?: string;
}

export interface UpdateLandingPageData {
  name?: string;
  slug?: string;
  html_content?: string;
  design_json?: Record<string, any>;
  css_content?: string;
  seo_title?: string;
  seo_description?: string;
  seo_keywords?: string;
  og_image?: File | null;
  favicon?: File | null;
  google_analytics_id?: string;
  facebook_pixel_id?: string;
  custom_head_code?: string;
  custom_body_code?: string;
  form_id?: string | null;
}

export interface SaveDesignData {
  html_content: string;
  design_json: Record<string, any>;
  css_content?: string;
}

export interface LandingPageFilters {
  search?: string;
  status?: LandingPageStatus;
  page?: number;
  page_size?: number;
}

export interface LandingPageListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: LandingPage[];
}

export interface LandingPageTemplate {
  id: string;
  name: string;
  description?: string;
  category: TemplateCategory;
  category_display?: string;
  thumbnail?: string;
  is_system: boolean;
  usage_count: number;
  // Detail only
  html_content?: string;
  design_json?: Record<string, any>;
  css_content?: string;
  created_at: string;
}

export interface LandingPageTemplateListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: LandingPageTemplate[];
}

export interface LandingPageAsset {
  id: string;
  file: string;
  file_type: 'image' | 'video' | 'document';
  file_name: string;
  file_size: number;
  mime_type: string;
  url: string;
  created_at: string;
}

export interface PageAnalytics {
  total_views: number;
  unique_views: number;
  conversion_count: number;
  conversion_rate: number;
  views_by_date: { date: string; views: number; unique_views: number }[];
}

export interface SaveAsTemplateData {
  landing_page_id: string;
  name: string;
  description?: string;
  category: TemplateCategory;
}
