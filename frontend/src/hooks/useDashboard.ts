import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/api/dashboard';

/** The dashboard, in one request. */
export const useDashboard = (days: number = 30) => {
  const query = useQuery({
    queryKey: ['dashboard', days],
    queryFn: () => dashboardApi.getDashboard(days),
    staleTime: 1000 * 60 * 5,
    // An alert that appeared five minutes ago should not wait for a reload.
    refetchInterval: 1000 * 60 * 5,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
};
