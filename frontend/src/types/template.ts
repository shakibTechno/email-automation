export interface EmailTemplate {
  id: string;
  name: string;
  description?: string;
  category: TemplateCategory;
  subject?: string;
  design_json: Record<string, any>;
  html_content?: string;
  thumbnail_url?: string;
  is_preset: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type TemplateCategory =
  | 'marketing'
  | 'transactional'
  | 'newsletter'
  | 'welcome'
  | 'notification'
  | 'custom';

export interface CreateTemplateData {
  name: string;
  description?: string;
  category: TemplateCategory;
  subject?: string;
  design_json: Record<string, any>;
  html_content?: string;
}

export interface UpdateTemplateData extends Partial<CreateTemplateData> {
  is_active?: boolean;
}

export interface TemplateImage {
  id: string;
  image: string;
  original_filename: string;
  file_size: number;
  width?: number;
  height?: number;
  created_at: string;
}

export interface TemplateFilters {
  search?: string;
  category?: TemplateCategory;
  is_preset?: boolean;
}

export interface TemplateListResponse {
  data: EmailTemplate[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
