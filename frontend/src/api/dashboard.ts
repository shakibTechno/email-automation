import { client } from './client';
import type { DashboardData } from '@/types/dashboard';

export const dashboardApi = {
  /** The whole dashboard in one request. */
  getDashboard: async (days: number = 30): Promise<DashboardData> => {
    const response = await client.get<DashboardData>('/dashboard/', {
      params: { days },
    });
    return response.data;
  },
};
