import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { templatesApi } from '@/api/templates';

export const useTemplateImages = () => {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['template-images'],
    queryFn: () => templatesApi.getImages(),
    staleTime: 30000,
  });

  const uploadMutation = useMutation({
    mutationFn: templatesApi.uploadImage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['template-images'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to upload image');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: templatesApi.deleteImage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['template-images'] });
      toast.success('Image deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete image');
    },
  });

  return {
    images: data?.data || [],
    total: data?.total || 0,
    isLoading,
    error,
    uploadImage: uploadMutation.mutateAsync,
    deleteImage: (id: string) => deleteMutation.mutate(id),
    isUploading: uploadMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
