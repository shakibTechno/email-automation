import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  getLandingPageAssets,
  uploadLandingPageAsset,
} from '@/api/landing-pages';

export const useLandingPageAssets = (pageId: string) => {
  const query = useQuery({
    queryKey: ['landing-page-assets', pageId],
    queryFn: () => getLandingPageAssets(pageId),
    enabled: !!pageId,
  });

  return {
    assets: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
};

export const useUploadAsset = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ pageId, file }: { pageId: string; file: File }) =>
      uploadLandingPageAsset(pageId, file),
    onSuccess: (_, { pageId }) => {
      queryClient.invalidateQueries({ queryKey: ['landing-page-assets', pageId] });
      toast.success('Asset uploaded successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to upload asset');
    },
  });
};
