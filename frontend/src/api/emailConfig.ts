import apiClient from './client';
import type {
  EmailConfig,
  UpdateEmailConfigData,
  SendingDomain,
  PostalTenant,
  DnsRecord,
} from '@/types/emailConfig';

export const emailConfigApi = {
  getConfig: async (): Promise<EmailConfig> => {
    const { data } = await apiClient.get('/email-config');
    return data;
  },

  updateConfig: async (payload: UpdateEmailConfigData): Promise<EmailConfig> => {
    const { data } = await apiClient.patch('/email-config', payload);
    return data;
  },

  testConnection: async (toEmail: string): Promise<{ success: boolean; message: string }> => {
    const { data } = await apiClient.post('/email-config/test', { to_email: toEmail });
    return data;
  },

  resumeSending: async (): Promise<void> => {
    await apiClient.post('/email-config/resume');
  },

  getDomains: async (): Promise<SendingDomain[]> => {
    const { data } = await apiClient.get('/email-config/domains');
    return data.results ?? data;
  },

  addDomain: async (domain: string): Promise<SendingDomain> => {
    const { data } = await apiClient.post('/email-config/domains', { domain });
    return data;
  },

  verifyDomain: async (
    id: string,
  ): Promise<{
    success: boolean;
    message: string;
    status: string;
    sending_enabled: boolean;
    dns_records: DnsRecord[];
  }> => {
    const { data } = await apiClient.post(`/email-config/domains/${id}/verify`);
    return data;
  },

  deleteDomain: async (id: string): Promise<void> => {
    await apiClient.delete(`/email-config/domains/${id}`);
  },

  /** null until the organization adds its first sending domain. */
  getTenant: async (): Promise<PostalTenant | null> => {
    const { data } = await apiClient.get('/email-config/tenant');
    return data.tenant ?? null;
  },

  syncTenant: async (): Promise<PostalTenant | null> => {
    const { data } = await apiClient.post('/email-config/tenant/sync');
    return data.tenant ?? null;
  },
};
