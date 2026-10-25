import apiClient from './client';
import type {
  AIConfig,
  GenerateRequest,
  GenerationJob,
  GenerationKind,
  UpdateAIConfigData,
} from '@/types/ai';

export const aiApi = {
  getConfig: async (): Promise<AIConfig> => {
    const { data } = await apiClient.get('/ai/config');
    return data;
  },

  updateConfig: async (payload: UpdateAIConfigData): Promise<AIConfig> => {
    const { data } = await apiClient.patch('/ai/config', payload);
    return data;
  },

  testConnection: async (): Promise<{ success: boolean; message: string; config: AIConfig }> => {
    const { data } = await apiClient.post('/ai/config/test');
    return data;
  },

  /** Queue a generation. The kind decides what gets built. */
  generate: async (kind: GenerationKind, payload: GenerateRequest): Promise<GenerationJob> => {
    const { data } = await apiClient.post(`/ai/generate/${kind}`, payload);
    return data;
  },

  getJob: async (id: string): Promise<GenerationJob> => {
    const { data } = await apiClient.get(`/ai/jobs/${id}`);
    return data;
  },
};

export default aiApi;
