import { client } from './client';
import type {
  LandingPage,
  LandingPageListResponse,
  CreateLandingPageData,
  UpdateLandingPageData,
  SaveDesignData,
  LandingPageFilters,
  LandingPageTemplate,
  LandingPageTemplateListResponse,
  LandingPageAsset,
  PageAnalytics,
  SaveAsTemplateData,
  TemplateCategory,
} from '@/types/landing-page';

// Landing Pages
export const getLandingPages = async (
  params?: LandingPageFilters
): Promise<LandingPageListResponse> => {
  const response = await client.get('/landing-pages/', { params });
  return response.data;
};

export const getLandingPage = async (id: string): Promise<LandingPage> => {
  const response = await client.get(`/landing-pages/${id}/`);
  return response.data;
};

export const createLandingPage = async (
  data: CreateLandingPageData
): Promise<LandingPage> => {
  const response = await client.post('/landing-pages/', data);
  return response.data;
};

export const updateLandingPage = async (
  id: string,
  data: UpdateLandingPageData
): Promise<LandingPage> => {
  // Handle file uploads with FormData
  if (data.og_image instanceof File || data.favicon instanceof File) {
    const formData = new FormData();
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (value instanceof File) {
          formData.append(key, value);
        } else if (typeof value === 'object') {
          formData.append(key, JSON.stringify(value));
        } else {
          formData.append(key, String(value));
        }
      }
    });
    const response = await client.patch(`/landing-pages/${id}/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  const response = await client.patch(`/landing-pages/${id}/`, data);
  return response.data;
};

export const deleteLandingPage = async (id: string): Promise<void> => {
  await client.delete(`/landing-pages/${id}/`);
};

export const publishLandingPage = async (id: string): Promise<LandingPage> => {
  const response = await client.post(`/landing-pages/${id}/publish/`);
  return response.data;
};

export const unpublishLandingPage = async (id: string): Promise<LandingPage> => {
  const response = await client.post(`/landing-pages/${id}/unpublish/`);
  return response.data;
};

export const duplicateLandingPage = async (id: string): Promise<LandingPage> => {
  const response = await client.post(`/landing-pages/${id}/duplicate/`);
  return response.data;
};

export const saveDesign = async (
  id: string,
  data: SaveDesignData
): Promise<LandingPage> => {
  const response = await client.patch(`/landing-pages/${id}/save_design/`, data);
  return response.data;
};

export const previewLandingPage = async (
  id: string
): Promise<{ html: string }> => {
  const response = await client.get(`/landing-pages/${id}/preview/`);
  return response.data;
};

export const getLandingPageAnalytics = async (
  id: string,
  days?: number
): Promise<PageAnalytics> => {
  const response = await client.get(`/landing-pages/${id}/analytics/`, {
    params: { days },
  });
  return response.data;
};

export const uploadLandingPageAsset = async (
  id: string,
  file: File
): Promise<LandingPageAsset> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await client.post(
    `/landing-pages/${id}/upload_asset/`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return response.data;
};

export const getLandingPageAssets = async (
  id: string
): Promise<LandingPageAsset[]> => {
  const response = await client.get(`/landing-pages/${id}/assets/`);
  return response.data;
};

// Templates
export const getLandingPageTemplates = async (params?: {
  category?: TemplateCategory;
  is_system?: boolean;
  search?: string;
}): Promise<LandingPageTemplateListResponse> => {
  const response = await client.get('/landing-page-templates/', { params });
  return response.data;
};

export const getLandingPageTemplate = async (
  id: string
): Promise<LandingPageTemplate> => {
  const response = await client.get(`/landing-page-templates/${id}/`);
  return response.data;
};

export const saveAsTemplate = async (
  data: SaveAsTemplateData
): Promise<LandingPageTemplate> => {
  const response = await client.post(
    '/landing-page-templates/save_as_template/',
    data
  );
  return response.data;
};
