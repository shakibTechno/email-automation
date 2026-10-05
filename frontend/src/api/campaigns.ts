import apiClient from './client';
import {
  Campaign,
  CampaignListResponse,
  CreateCampaignData,
  UpdateCampaignData,
  CampaignFilters,
  CampaignSendData,
  CampaignTestEmailData,
  CampaignRecipient,
  ABTest,
  ABTestConfig,
} from '@/types/campaign';
import { PaginationParams } from '@/types/api';

export const campaignsApi = {
  getCampaigns: async (
    params?: CampaignFilters & PaginationParams
  ): Promise<CampaignListResponse> => {
    const response = await apiClient.get('/campaigns', { params });
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

  getCampaign: async (id: string): Promise<Campaign> => {
    const response = await apiClient.get<Campaign>(`/campaigns/${id}`);
    return response.data;
  },

  createCampaign: async (data: CreateCampaignData): Promise<Campaign> => {
    const response = await apiClient.post<Campaign>('/campaigns', data);
    return response.data;
  },

  updateCampaign: async (
    id: string,
    data: UpdateCampaignData
  ): Promise<Campaign> => {
    const response = await apiClient.patch<Campaign>(
      `/campaigns/${id}`,
      data
    );
    return response.data;
  },

  deleteCampaign: async (id: string): Promise<void> => {
    await apiClient.delete(`/campaigns/${id}`);
  },

  duplicateCampaign: async (id: string): Promise<Campaign> => {
    const response = await apiClient.post<Campaign>(
      `/campaigns/${id}/duplicate`
    );
    return response.data;
  },

  sendCampaign: async (
    id: string,
    data: CampaignSendData
  ): Promise<Campaign> => {
    const response = await apiClient.post<Campaign>(
      `/campaigns/${id}/send`,
      data
    );
    return response.data;
  },

  pauseCampaign: async (id: string): Promise<Campaign> => {
    const response = await apiClient.post<Campaign>(
      `/campaigns/${id}/pause`
    );
    return response.data;
  },

  cancelCampaign: async (id: string): Promise<Campaign> => {
    const response = await apiClient.post<Campaign>(
      `/campaigns/${id}/cancel`
    );
    return response.data;
  },

  archiveCampaign: async (id: string): Promise<Campaign> => {
    const response = await apiClient.post<Campaign>(
      `/campaigns/${id}/archive`
    );
    return response.data;
  },

  sendTestEmail: async (
    id: string,
    data: CampaignTestEmailData
  ): Promise<{ message: string; recipients: string[] }> => {
    const response = await apiClient.post(
      `/campaigns/${id}/send_test`,
      data
    );
    return response.data;
  },

  previewCampaign: async (
    id: string
  ): Promise<{ html: string; subject: string }> => {
    const response = await apiClient.get(`/campaigns/${id}/preview`);
    return response.data;
  },

  getCampaignRecipients: async (
    id: string,
    params?: PaginationParams
  ): Promise<{ data: CampaignRecipient[]; total: number }> => {
    const response = await apiClient.get(
      `/campaigns/${id}/recipients`,
      { params }
    );
    const raw = response.data;
    return {
      data: raw.results ?? raw,
      total: raw.count ?? 0,
    };
  },

  getABTest: async (campaignId: string): Promise<ABTest | null> => {
    try {
      const response = await apiClient.get<ABTest>(`/campaigns/${campaignId}/ab-test`);
      return response.data;
    } catch (err: any) {
      if (err?.response?.status === 404) return null;
      throw err;
    }
  },

  saveABTest: async (campaignId: string, data: ABTestConfig): Promise<ABTest> => {
    const response = await apiClient.post<ABTest>(`/campaigns/${campaignId}/ab-test`, data);
    return response.data;
  },

  deleteABTest: async (campaignId: string): Promise<void> => {
    await apiClient.delete(`/campaigns/${campaignId}/ab-test`);
  },

  declareWinner: async (campaignId: string, winner: 'a' | 'b'): Promise<ABTest> => {
    const response = await apiClient.post<ABTest>(
      `/campaigns/${campaignId}/declare-winner`,
      { winner }
    );
    return response.data;
  },
};

export default campaignsApi;
