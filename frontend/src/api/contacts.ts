import apiClient from './client';
import {
  Contact,
  ContactListResponse,
  CreateContactData,
  UpdateContactData,
  ContactFilters,
  BulkActionData,
  TimelineResponse,
  DuplicatesResponse,
} from '@/types/contact';
import { ApiResponse, PaginationParams } from '@/types/api';

export const contactsApi = {
  getContacts: async (
    params?: ContactFilters & PaginationParams
  ): Promise<ContactListResponse> => {
    const response = await apiClient.get('/contacts', { params });
    const raw = response.data;
    // DRF returns: { count, next, previous, results }
    // Map to our ContactListResponse format
    const pageSize = params?.page_size ?? 20;
    return {
      data: raw.results ?? raw,
      total: raw.count ?? 0,
      page: params?.page ?? 1,
      per_page: pageSize,
      total_pages: Math.ceil((raw.count ?? 0) / pageSize),
    };
  },

  getContact: async (id: string): Promise<Contact> => {
    const response = await apiClient.get<Contact>(`/contacts/${id}`);
    return response.data;
  },

  createContact: async (data: CreateContactData): Promise<Contact> => {
    const response = await apiClient.post<Contact>('/contacts', data);
    return response.data;
  },

  updateContact: async (id: string, data: UpdateContactData): Promise<Contact> => {
    const response = await apiClient.put<Contact>(`/contacts/${id}`, data);
    return response.data;
  },

  deleteContact: async (id: string): Promise<void> => {
    await apiClient.delete(`/contacts/${id}`);
  },

  bulkAction: async (data: BulkActionData): Promise<ApiResponse<{ message: string }>> => {
    const response = await apiClient.post<ApiResponse<{ message: string }>>('/contacts/bulk', data);
    return response.data;
  },

  exportContacts: async (filters?: ContactFilters): Promise<Blob> => {
    const response = await apiClient.get('/contacts/export', {
      params: filters,
      responseType: 'blob',
    });
    return response.data;
  },

  importContacts: async (formData: FormData): Promise<{
    message: string;
    results: {
      imported: number;
      updated: number;
      skipped: number;
      errors: Array<{ row: number; error: string }>;
    };
  }> => {
    const response = await apiClient.post('/contacts/import_csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  getDuplicates: async (): Promise<DuplicatesResponse> => {
    const response = await apiClient.get('/contacts/duplicates');
    return response.data;
  },

  mergeContacts: async (data: {
    primary_contact_id: string;
    duplicate_contact_ids: string[];
  }): Promise<{ message: string; contact: Contact }> => {
    const response = await apiClient.post('/contacts/merge', data);
    return response.data;
  },

  getContactTimeline: async (
    id: string,
    params?: { limit?: number; offset?: number }
  ): Promise<TimelineResponse> => {
    const response = await apiClient.get(`/contacts/${id}/activity-timeline`, { params });
    return response.data;
  },
};

export default contactsApi;
