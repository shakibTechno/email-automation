import apiClient from './client';
import {
  EmailTemplate,
  TemplateListResponse,
  CreateTemplateData,
  UpdateTemplateData,
  TemplateFilters,
  TemplateImage,
} from '@/types/template';
import { PaginationParams } from '@/types/api';

export const templatesApi = {
  getTemplates: async (
    params?: TemplateFilters & PaginationParams
  ): Promise<TemplateListResponse> => {
    const response = await apiClient.get('/templates', { params });
    const raw = response.data;
    const pageSize = params?.page_size ?? 20;
    return {
      data: raw.results ?? raw,
      total: raw.count ?? 0,
      page: params?.page ?? 1,
      per_page: pageSize,
      total_pages: Math.ceil((raw.count ?? 0) / pageSize),
    };
  },

  getTemplate: async (id: string): Promise<EmailTemplate> => {
    const response = await apiClient.get<EmailTemplate>(`/templates/${id}`);
    return response.data;
  },

  createTemplate: async (data: CreateTemplateData): Promise<EmailTemplate> => {
    const response = await apiClient.post<EmailTemplate>('/templates', data);
    return response.data;
  },

  updateTemplate: async (
    id: string,
    data: UpdateTemplateData
  ): Promise<EmailTemplate> => {
    const response = await apiClient.patch<EmailTemplate>(
      `/templates/${id}`,
      data
    );
    return response.data;
  },

  deleteTemplate: async (id: string): Promise<void> => {
    await apiClient.delete(`/templates/${id}`);
  },

  duplicateTemplate: async (id: string): Promise<EmailTemplate> => {
    const response = await apiClient.post<EmailTemplate>(
      `/templates/${id}/duplicate`
    );
    return response.data;
  },

  // Image operations
  getImages: async (
    params?: PaginationParams
  ): Promise<{ data: TemplateImage[]; total: number }> => {
    const response = await apiClient.get('/template-images', { params });
    const raw = response.data;
    return {
      data: raw.results ?? raw,
      total: raw.count ?? 0,
    };
  },

  uploadImage: async (formData: FormData): Promise<TemplateImage> => {
    const response = await apiClient.post<TemplateImage>(
      '/template-images',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  deleteImage: async (id: string): Promise<void> => {
    await apiClient.delete(`/template-images/${id}`);
  },
};

export default templatesApi;
