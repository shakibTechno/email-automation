import apiClient from './client';
import { CustomField } from '@/types/contact';

interface Paginated<T> {
  results: T[];
  count: number;
}

const BASE_URL = '/custom-fields';

/**
 * The list endpoint is paginated, so it answers {results, count} — this used to
 * be typed and returned as a bare array, which meant anything reading it got an
 * object where it expected a list.
 */
export const customFieldsApi = {
  getCustomFields: async (): Promise<CustomField[]> => {
    const { data } = await apiClient.get<Paginated<CustomField>>(BASE_URL);
    return data.results ?? [];
  },

  getCustomField: async (id: string): Promise<CustomField> => {
    const { data } = await apiClient.get<CustomField>(`${BASE_URL}/${id}`);
    return data;
  },

  createCustomField: async (payload: Partial<CustomField>): Promise<CustomField> => {
    const { data } = await apiClient.post<CustomField>(BASE_URL, payload);
    return data;
  },

  updateCustomField: async (
    id: string,
    payload: Partial<CustomField>
  ): Promise<CustomField> => {
    // PATCH, not PUT: a rename should send the name, not every field — and
    // `key` is read-only, so a full PUT would have to echo it back.
    const { data } = await apiClient.patch<CustomField>(`${BASE_URL}/${id}`, payload);
    return data;
  },

  deleteCustomField: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE_URL}/${id}`);
  },
};

export default customFieldsApi;
