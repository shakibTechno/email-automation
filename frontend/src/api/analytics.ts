/**
 * API client for Analytics & Reporting module
 */
import apiClient from './client';
import type {
  AnalyticsOverview,
  CampaignAnalyticsListResponse,
  CampaignDetailAnalytics,
  ContactAnalytics,
  FormAnalytics,
  LandingPageAnalytics,
} from '@/types/analytics';

const BASE_URL = '/analytics';

export async function getAnalyticsOverview(days: number = 30): Promise<AnalyticsOverview> {
  const response = await apiClient.get<AnalyticsOverview>(BASE_URL, {
    params: { days },
  });
  return response.data;
}

export async function getCampaignAnalytics(days: number = 30): Promise<CampaignAnalyticsListResponse> {
  const response = await apiClient.get<CampaignAnalyticsListResponse>(`${BASE_URL}/campaigns`, {
    params: { days },
  });
  return response.data;
}

export async function getCampaignDetail(id: string): Promise<CampaignDetailAnalytics> {
  const response = await apiClient.get<CampaignDetailAnalytics>(`${BASE_URL}/campaigns/${id}`);
  return response.data;
}

export async function getCampaignComparison(ids: string[]): Promise<CampaignDetailAnalytics[]> {
  const response = await apiClient.get<CampaignDetailAnalytics[]>(`${BASE_URL}/campaigns/compare`, {
    params: { ids: ids.join(',') },
  });
  return response.data;
}

export async function exportCampaignReport(id: string): Promise<Blob> {
  const response = await apiClient.get(`${BASE_URL}/campaigns/${id}/export`, {
    responseType: 'blob',
  });
  return response.data;
}

export async function getContactAnalytics(days: number = 30): Promise<ContactAnalytics> {
  const response = await apiClient.get<ContactAnalytics>(`${BASE_URL}/contacts`, {
    params: { days },
  });
  return response.data;
}

export async function getFormAnalytics(days: number = 30): Promise<FormAnalytics> {
  const response = await apiClient.get<FormAnalytics>(`${BASE_URL}/forms`, {
    params: { days },
  });
  return response.data;
}

export async function getLandingPageAnalytics(days: number = 30): Promise<LandingPageAnalytics> {
  const response = await apiClient.get<LandingPageAnalytics>(`${BASE_URL}/landing-pages`, {
    params: { days },
  });
  return response.data;
}
