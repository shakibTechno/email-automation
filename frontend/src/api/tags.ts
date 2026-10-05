import apiClient from './client';
import { Tag, CreateTagData, UpdateTagData } from '@/types/contact';

export const tagsApi = {
  getTags: async (): Promise<Tag[]> => {
    const response = await apiClient.get('/tags');
    // DRF returns paginated response: { count, next, previous, results }
    return response.data.results ?? response.data;
  },

  getTag: async (id: string): Promise<Tag> => {
    const response = await apiClient.get<Tag>(`/tags/${id}`);
    return response.data;
  },

  createTag: async (data: CreateTagData): Promise<Tag> => {
    const response = await apiClient.post<Tag>('/tags', data);
    return response.data;
  },

  updateTag: async (id: string, data: UpdateTagData): Promise<Tag> => {
    const response = await apiClient.put<Tag>(`/tags/${id}`, data);
    return response.data;
  },

  deleteTag: async (id: string): Promise<void> => {
    await apiClient.delete(`/tags/${id}`);
  },
};

export default tagsApi;
