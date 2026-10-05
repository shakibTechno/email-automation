import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { campaignsApi } from '@/api/campaigns';
import {
  CampaignFilters,
  UpdateCampaignData,
  CampaignSendData,
  CampaignTestEmailData,
  ABTestConfig,
} from '@/types/campaign';
import { PaginationParams } from '@/types/api';

export const useCampaigns = (filters?: CampaignFilters & PaginationParams) => {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['campaigns', filters],
    queryFn: () => campaignsApi.getCampaigns(filters),
    staleTime: 30000,
    // Poll every 5s when any campaign in the list is actively sending
    refetchInterval: (query) => {
      const campaigns = query.state.data?.data ?? [];
      return campaigns.some((c) => c.status === 'sending') ? 5000 : false;
    },
  });

  const createMutation = useMutation({
    mutationFn: campaignsApi.createCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Campaign created successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create campaign');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCampaignData }) =>
      campaignsApi.updateCampaign(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaign', variables.id] });
      toast.success('Campaign updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update campaign');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: campaignsApi.deleteCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Campaign deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete campaign');
    },
  });

  const duplicateMutation = useMutation({
    mutationFn: campaignsApi.duplicateCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Campaign duplicated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to duplicate campaign');
    },
  });

  const sendMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CampaignSendData }) =>
      campaignsApi.sendCampaign(id, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaign'] });
      const msg =
        result.status === 'scheduled'
          ? 'Campaign scheduled successfully!'
          : 'Campaign is now sending!';
      toast.success(msg);
    },
    onError: (error: any) => {
      toast.error(error.message || error.errors?.join(', ') || 'Failed to send campaign');
    },
  });

  const pauseMutation = useMutation({
    mutationFn: campaignsApi.pauseCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaign'] });
      toast.success('Campaign paused.');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to pause campaign');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: campaignsApi.cancelCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaign'] });
      toast.success('Campaign cancelled.');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to cancel campaign');
    },
  });

  const archiveMutation = useMutation({
    mutationFn: campaignsApi.archiveCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaign'] });
      toast.success('Campaign archived.');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to archive campaign');
    },
  });

  const sendTestMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CampaignTestEmailData }) =>
      campaignsApi.sendTestEmail(id, data),
    onSuccess: (result) => {
      toast.success(result.message || 'Test email sent!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to send test email');
    },
  });

  return {
    campaigns: data?.data || [],
    total: data?.total || 0,
    page: data?.page || 1,
    perPage: data?.per_page || 20,
    totalPages: data?.total_pages || 0,
    isLoading,
    error,
    createCampaign: createMutation.mutateAsync,
    updateCampaign: (id: string, data: UpdateCampaignData) =>
      updateMutation.mutateAsync({ id, data }),
    deleteCampaign: (id: string) => deleteMutation.mutate(id),
    duplicateCampaign: (id: string) => duplicateMutation.mutate(id),
    sendCampaign: (id: string, data: CampaignSendData) =>
      sendMutation.mutateAsync({ id, data }),
    pauseCampaign: (id: string) => pauseMutation.mutate(id),
    cancelCampaign: (id: string) => cancelMutation.mutate(id),
    archiveCampaign: (id: string) => archiveMutation.mutate(id),
    sendTestEmail: (id: string, data: CampaignTestEmailData) =>
      sendTestMutation.mutateAsync({ id, data }),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isDuplicating: duplicateMutation.isPending,
    isSending: sendMutation.isPending,
    isSendingTest: sendTestMutation.isPending,
  };
};

export const useCampaign = (id: string) => {
  const { data: campaign, isLoading, error } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => campaignsApi.getCampaign(id),
    enabled: !!id,
    // Poll every 3s while the campaign is actively sending so the progress bar stays live
    refetchInterval: (query) =>
      query.state.data?.status === 'sending' ? 3000 : false,
  });

  return {
    campaign,
    isLoading,
    error,
  };
};

export const useABTest = (campaignId: string) => {
  const queryClient = useQueryClient();

  const saveMutation = useMutation({
    mutationFn: (data: ABTestConfig) => campaignsApi.saveABTest(campaignId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      toast.success('A/B test configuration saved.');
    },
    onError: (error: any) => {
      const detail = error?.response?.data;
      const msg = detail?.non_field_errors?.[0]
        || Object.values(detail ?? {})[0]
        || error.message
        || 'Failed to save A/B test.';
      toast.error(String(msg));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => campaignsApi.deleteABTest(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      toast.success('A/B test removed.');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to remove A/B test.');
    },
  });

  const declareWinnerMutation = useMutation({
    mutationFn: (winner: 'a' | 'b') => campaignsApi.declareWinner(campaignId, winner),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      toast.success('Winner declared! Sending to remaining recipients…');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to declare winner.');
    },
  });

  return {
    saveABTest: saveMutation.mutateAsync,
    deleteABTest: deleteMutation.mutate,
    declareWinner: declareWinnerMutation.mutateAsync,
    isSaving: saveMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isDeclaring: declareWinnerMutation.isPending,
  };
};
