import { client } from './client';
import type { DashboardData, DashboardOverview, CampaignStats, ContactGrowthData } from '@/types/dashboard';

export const dashboardApi = {
  /**
   * Get all dashboard data
   */
  getDashboard: async (days: number = 30): Promise<DashboardData> => {
    const response = await client.get<DashboardData>('/dashboard/', {
      params: { days },
    });
    return response.data;
  },

  /**
   * Get overview statistics only
   */
  getOverview: async (): Promise<DashboardOverview> => {
    const response = await client.get<DashboardOverview>('/dashboard/overview/');
    return response.data;
  },

  /**
   * Get campaign statistics
   */
  getCampaignStats: async (days: number = 30): Promise<CampaignStats> => {
    const response = await client.get<CampaignStats>('/dashboard/campaigns/', {
      params: { days },
    });
    return response.data;
  },

  /**
   * Get contact growth data
   */
  getContactGrowth: async (days: number = 30): Promise<ContactGrowthData[]> => {
    const response = await client.get<ContactGrowthData[]>('/dashboard/contacts/', {
      params: { days },
    });
    return response.data;
  },
};
