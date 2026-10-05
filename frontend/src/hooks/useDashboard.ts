import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/api/dashboard';

/**
 * Hook for fetching all dashboard data
 */
export const useDashboard = (days: number = 30) => {
  const query = useQuery({
    queryKey: ['dashboard', days],
    queryFn: () => dashboardApi.getDashboard(days),
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 1000 * 60 * 5, // Refetch every 5 minutes
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
};

/**
 * Hook for fetching overview stats only
 */
export const useDashboardOverview = () => {
  const query = useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: dashboardApi.getOverview,
    staleTime: 1000 * 60 * 5,
  });

  return {
    overview: query.data,
    isLoading: query.isLoading,
  };
};

/**
 * Hook for fetching campaign stats
 */
export const useCampaignStats = (days: number = 30) => {
  const query = useQuery({
    queryKey: ['dashboard', 'campaigns', days],
    queryFn: () => dashboardApi.getCampaignStats(days),
    staleTime: 1000 * 60 * 5,
  });

  return {
    campaignStats: query.data,
    isLoading: query.isLoading,
  };
};

/**
 * Hook for fetching contact growth
 */
export const useContactGrowth = (days: number = 30) => {
  const query = useQuery({
    queryKey: ['dashboard', 'contacts', days],
    queryFn: () => dashboardApi.getContactGrowth(days),
    staleTime: 1000 * 60 * 5,
  });

  return {
    contactGrowth: query.data,
    isLoading: query.isLoading,
  };
};
