/**
 * React Query hooks for Analytics & Reporting module
 */
import { useMutation, useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as analyticsApi from '@/api/analytics';

const STALE_TIME = 1000 * 60 * 5; // 5 minutes

export const analyticsKeys = {
  all: ['analytics'] as const,
  overview: (days: number) => [...analyticsKeys.all, 'overview', days] as const,
  campaigns: (days: number) => [...analyticsKeys.all, 'campaigns', days] as const,
  campaignDetail: (id: string) => [...analyticsKeys.all, 'campaign', id] as const,
  campaignComparison: (ids: string[]) => [...analyticsKeys.all, 'comparison', ids] as const,
  contacts: (days: number) => [...analyticsKeys.all, 'contacts', days] as const,
  forms: (days: number) => [...analyticsKeys.all, 'forms', days] as const,
  landingPages: (days: number) => [...analyticsKeys.all, 'landing-pages', days] as const,
};

export function useAnalyticsOverview(days: number = 30) {
  return useQuery({
    queryKey: analyticsKeys.overview(days),
    queryFn: () => analyticsApi.getAnalyticsOverview(days),
    staleTime: STALE_TIME,
  });
}

export function useCampaignAnalytics(days: number = 30) {
  return useQuery({
    queryKey: analyticsKeys.campaigns(days),
    queryFn: () => analyticsApi.getCampaignAnalytics(days),
    staleTime: STALE_TIME,
  });
}

export function useCampaignDetail(id: string) {
  return useQuery({
    queryKey: analyticsKeys.campaignDetail(id),
    queryFn: () => analyticsApi.getCampaignDetail(id),
    enabled: !!id,
    staleTime: STALE_TIME,
  });
}

export function useCampaignComparison(ids: string[]) {
  return useQuery({
    queryKey: analyticsKeys.campaignComparison(ids),
    queryFn: () => analyticsApi.getCampaignComparison(ids),
    enabled: ids.length >= 2,
    staleTime: STALE_TIME,
  });
}

export function useExportCampaignReport() {
  return useMutation({
    mutationFn: async ({ id, name }: { id: string; name: string }) => {
      const blob = await analyticsApi.exportCampaignReport(id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `campaign_${name.replace(/\s+/g, '_')}_${id}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
    onSuccess: () => {
      toast.success('Campaign report exported successfully');
    },
    onError: () => {
      toast.error('Failed to export campaign report');
    },
  });
}

export function useContactAnalytics(days: number = 30) {
  return useQuery({
    queryKey: analyticsKeys.contacts(days),
    queryFn: () => analyticsApi.getContactAnalytics(days),
    staleTime: STALE_TIME,
  });
}

export function useFormAnalytics(days: number = 30) {
  return useQuery({
    queryKey: analyticsKeys.forms(days),
    queryFn: () => analyticsApi.getFormAnalytics(days),
    staleTime: STALE_TIME,
  });
}

export function useLandingPageAnalytics(days: number = 30) {
  return useQuery({
    queryKey: analyticsKeys.landingPages(days),
    queryFn: () => analyticsApi.getLandingPageAnalytics(days),
    staleTime: STALE_TIME,
  });
}
