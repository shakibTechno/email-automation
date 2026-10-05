import { useQuery } from '@tanstack/react-query';
import { campaignsApi } from '@/api/campaigns';
import { PaginationParams } from '@/types/api';

export const useCampaignRecipients = (
  campaignId: string,
  params?: PaginationParams,
  isSending?: boolean
) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['campaign-recipients', campaignId, params],
    queryFn: () => campaignsApi.getCampaignRecipients(campaignId, params),
    enabled: !!campaignId,
    // Refresh the recipient table while the campaign is being sent
    refetchInterval: isSending ? 5000 : false,
  });

  return {
    recipients: data?.data || [],
    total: data?.total || 0,
    isLoading,
    error,
  };
};
