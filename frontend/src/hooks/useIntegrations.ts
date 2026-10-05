import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { integrationsApi } from '@/api/integrations';
import { toast } from 'sonner';
import type {
  AnalyticsProvider,
  UpsertAnalyticsData,
  UpdateCredentialsData,
  DemoConnectData,
  UpdateSocialData,
} from '@/types/integration';

const INTEGRATION_KEYS = {
  all: ['integrations'] as const,
  analytics: () => [...INTEGRATION_KEYS.all, 'analytics'] as const,
  social: () => [...INTEGRATION_KEYS.all, 'social'] as const,
  syncHistory: (id: string) => [...INTEGRATION_KEYS.all, 'sync-history', id] as const,
  fieldMappingOptions: () => [...INTEGRATION_KEYS.all, 'field-mapping-options'] as const,
};

export function useAnalyticsIntegrations() {
  return useQuery({
    queryKey: INTEGRATION_KEYS.analytics(),
    queryFn: integrationsApi.getAnalyticsIntegrations,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useSocialIntegrations() {
  return useQuery({
    queryKey: INTEGRATION_KEYS.social(),
    queryFn: integrationsApi.getSocialIntegrations,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useSyncHistory(id: string, enabled: boolean) {
  return useQuery({
    queryKey: INTEGRATION_KEYS.syncHistory(id),
    queryFn: () => integrationsApi.getSyncHistory(id),
    staleTime: 60 * 1000, // 1 minute
    enabled,
  });
}

export function useFieldMappingOptions() {
  return useQuery({
    queryKey: INTEGRATION_KEYS.fieldMappingOptions(),
    queryFn: integrationsApi.getFieldMappingOptions,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

export function useIntegrationMutations() {
  const queryClient = useQueryClient();

  const invalidateAnalytics = () => {
    queryClient.invalidateQueries({ queryKey: INTEGRATION_KEYS.analytics() });
  };

  const invalidateSocial = () => {
    queryClient.invalidateQueries({ queryKey: INTEGRATION_KEYS.social() });
  };

  const upsertAnalyticsMutation = useMutation({
    mutationFn: (data: UpsertAnalyticsData) => integrationsApi.upsertAnalytics(data),
    onSuccess: () => {
      toast.success('Analytics integration saved');
      invalidateAnalytics();
    },
    onError: () => {
      toast.error('Failed to save analytics integration');
    },
  });

  const deleteAnalyticsMutation = useMutation({
    mutationFn: (provider: AnalyticsProvider) => integrationsApi.deleteAnalytics(provider),
    onSuccess: () => {
      toast.success('Analytics integration removed');
      invalidateAnalytics();
    },
    onError: () => {
      toast.error('Failed to remove analytics integration');
    },
  });

  const demoConnectMutation = useMutation({
    mutationFn: (data: DemoConnectData) => integrationsApi.demoConnect(data),
    onSuccess: () => {
      toast.success('Connected in demo mode');
      invalidateSocial();
    },
    onError: () => {
      toast.error('Failed to connect integration');
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: (id: string) => integrationsApi.disconnectIntegration(id),
    onSuccess: () => {
      toast.success('Integration disconnected');
      invalidateSocial();
    },
    onError: () => {
      toast.error('Failed to disconnect integration');
    },
  });

  const updateSocialMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateSocialData }) =>
      integrationsApi.updateSocialIntegration(id, data),
    onSuccess: () => {
      toast.success('Integration settings updated');
      invalidateSocial();
    },
    onError: () => {
      toast.error('Failed to update integration settings');
    },
  });

  const updateCredentialsMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCredentialsData }) =>
      integrationsApi.updateCredentials(id, data),
    onSuccess: () => {
      toast.success('API credentials saved');
      invalidateSocial();
    },
    onError: () => {
      toast.error('Failed to save API credentials');
    },
  });

  const connectMutation = useMutation({
    mutationFn: (id: string) => integrationsApi.connectIntegration(id),
    onSuccess: () => {
      toast.success('Integration connected');
      invalidateSocial();
    },
    onError: () => {
      toast.error('Failed to connect integration. Check your API credentials.');
    },
  });

  const syncLeadsMutation = useMutation({
    mutationFn: (id: string) => integrationsApi.syncLeads(id),
    onSuccess: (_data, id) => {
      toast.success('Lead sync completed');
      invalidateSocial();
      queryClient.invalidateQueries({ queryKey: INTEGRATION_KEYS.syncHistory(id) });
    },
    onError: () => {
      toast.error('Failed to sync leads');
    },
  });

  return {
    upsertAnalytics: upsertAnalyticsMutation,
    deleteAnalytics: deleteAnalyticsMutation,
    demoConnect: demoConnectMutation,
    disconnect: disconnectMutation,
    updateSocial: updateSocialMutation,
    updateCredentials: updateCredentialsMutation,
    connect: connectMutation,
    syncLeads: syncLeadsMutation,
  };
}
