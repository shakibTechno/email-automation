import apiClient from './client';
import { CustomField } from '@/types/contact';

export const customFieldsApi = {
  getCustomFields: async (): Promise<CustomField[]> => {
    const response = await apiClient.get<CustomField[]>('/custom-fields');
    return response.data;
  },

  getCustomField: async (id: string): Promise<CustomField> => {
    const response = await apiClient.get<CustomField>(`/custom-fields/${id}`);
    return response.data;
  },

  createCustomField: async (data: Partial<CustomField>): Promise<CustomField> => {
    const response = await apiClient.post<CustomField>('/custom-fields', data);
    return response.data;
  },

  updateCustomField: async (id: string, data: Partial<CustomField>): Promise<CustomField> => {
    const response = await apiClient.put<CustomField>(`/custom-fields/${id}`, data);
    return response.data;
  },

  deleteCustomField: async (id: string): Promise<void> => {
    await apiClient.delete(`/custom-fields/${id}`);
  },
};

export default customFieldsApi;
