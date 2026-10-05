import { apiClient } from './client';
import type {
  AnalyticsIntegration,
  AnalyticsProvider,
  UpsertAnalyticsData,
  SocialIntegration,
  UpdateSocialData,
  UpdateCredentialsData,
  LeadSyncLog,
  DemoConnectData,
  FieldMappingOption,
} from '@/types/integration';

const BASE = '/integrations';

export const integrationsApi = {
  // Analytics
  getAnalyticsIntegrations: async (): Promise<AnalyticsIntegration[]> => {
    const { data } = await apiClient.get(`${BASE}/analytics`);
    return data;
  },

  upsertAnalytics: async (payload: UpsertAnalyticsData): Promise<AnalyticsIntegration> => {
    const { data } = await apiClient.post(`${BASE}/analytics/upsert`, payload);
    return data;
  },

  deleteAnalytics: async (provider: AnalyticsProvider): Promise<void> => {
    await apiClient.delete(`${BASE}/analytics/${provider}`);
  },

  // Social
  getSocialIntegrations: async (): Promise<SocialIntegration[]> => {
    const { data } = await apiClient.get(`${BASE}/social`);
    return data;
  },

  updateSocialIntegration: async (id: string, payload: UpdateSocialData): Promise<SocialIntegration> => {
    const { data } = await apiClient.patch(`${BASE}/social/${id}`, payload);
    return data;
  },

  disconnectIntegration: async (id: string): Promise<void> => {
    await apiClient.post(`${BASE}/social/${id}/disconnect`);
  },

  syncLeads: async (id: string): Promise<LeadSyncLog> => {
    const { data } = await apiClient.post(`${BASE}/social/${id}/sync`);
    return data;
  },

  getSyncHistory: async (id: string): Promise<LeadSyncLog[]> => {
    const { data } = await apiClient.get(`${BASE}/social/${id}/sync-history`);
    return data;
  },

  updateCredentials: async (id: string, payload: UpdateCredentialsData): Promise<SocialIntegration> => {
    const { data } = await apiClient.post(`${BASE}/social/${id}/credentials`, payload);
    return data;
  },

  connectIntegration: async (id: string): Promise<SocialIntegration> => {
    const { data } = await apiClient.post(`${BASE}/social/${id}/connect`);
    return data;
  },

  // Other
  demoConnect: async (payload: DemoConnectData): Promise<SocialIntegration> => {
    const { data } = await apiClient.post(`${BASE}/social/demo-connect`, payload);
    return data;
  },

  getFieldMappingOptions: async (): Promise<FieldMappingOption[]> => {
    const { data } = await apiClient.get(`${BASE}/field-mapping-options`);
    return data;
  },
};
