import { useQuery } from '@tanstack/react-query';
import { getLandingPageAnalytics } from '@/api/landing-pages';

export const useLandingPageAnalytics = (pageId: string, days?: number) => {
  const query = useQuery({
    queryKey: ['landing-page-analytics', pageId, days],
    queryFn: () => getLandingPageAnalytics(pageId, days),
    enabled: !!pageId,
  });

  return {
    analytics: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
};
