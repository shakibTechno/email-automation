import apiClient from './client';
import axios from 'axios';
import {
  Form,
  FormListResponse,
  CreateFormData,
  UpdateFormData,
  FormFilters,
  FormSubmission,
  FormSubmissionListResponse,
  PublicFormData,
  EmbedCodeResponse,
  ShareUrlResponse,
} from '@/types/form';
import { PaginationParams } from '@/types/api';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Public client without auth headers
const publicClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,
});

// Add trailing slash interceptor for public client
publicClient.interceptors.request.use((config) => {
  if (config.url && !config.url.endsWith('/') && !config.url.includes('?')) {
    config.url = `${config.url}/`;
  }
  return config;
});

export const formsApi = {
  // Authenticated endpoints
  getForms: async (
    params?: FormFilters & PaginationParams
  ): Promise<FormListResponse> => {
    const response = await apiClient.get('/forms', { params });
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

  getForm: async (id: string): Promise<Form> => {
    const response = await apiClient.get<Form>(`/forms/${id}`);
    return response.data;
  },

  createForm: async (data: CreateFormData): Promise<Form> => {
    const response = await apiClient.post<Form>('/forms', data);
    return response.data;
  },

  updateForm: async (id: string, data: UpdateFormData): Promise<Form> => {
    const response = await apiClient.patch<Form>(`/forms/${id}`, data);
    return response.data;
  },

  deleteForm: async (id: string): Promise<void> => {
    await apiClient.delete(`/forms/${id}`);
  },

  duplicateForm: async (id: string): Promise<Form> => {
    const response = await apiClient.post<Form>(`/forms/${id}/duplicate`);
    return response.data;
  },

  toggleFormStatus: async (id: string): Promise<Form> => {
    const response = await apiClient.post<Form>(`/forms/${id}/toggle_status`);
    return response.data;
  },

  getFormSubmissions: async (
    id: string,
    params?: PaginationParams
  ): Promise<FormSubmissionListResponse> => {
    const response = await apiClient.get(`/forms/${id}/submissions`, { params });
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

  getSubmissionDetail: async (
    formId: string,
    submissionId: string
  ): Promise<FormSubmission> => {
    const response = await apiClient.get<FormSubmission>(
      `/forms/${formId}/submissions/${submissionId}`
    );
    return response.data;
  },

  exportSubmissions: async (id: string): Promise<Blob> => {
    const response = await apiClient.get(`/forms/${id}/export_submissions`, {
      responseType: 'blob',
    });
    return response.data;
  },

  getEmbedCode: async (id: string): Promise<EmbedCodeResponse> => {
    const response = await apiClient.get<EmbedCodeResponse>(
      `/forms/${id}/embed_code`
    );
    return response.data;
  },

  getShareUrl: async (id: string): Promise<ShareUrlResponse> => {
    const response = await apiClient.get<ShareUrlResponse>(
      `/forms/${id}/share_url`
    );
    return response.data;
  },

  // Public endpoints (no auth)
  getPublicForm: async (id: string): Promise<Form> => {
    const response = await publicClient.get<Form>(`/public/forms/${id}`);
    return response.data;
  },

  submitPublicForm: async (
    id: string,
    data: PublicFormData
  ): Promise<{ message: string; redirect_url?: string; submission_id: string }> => {
    const response = await publicClient.post(
      `/public/forms/${id}/submit`,
      data
    );
    return response.data;
  },
};

export default formsApi;
