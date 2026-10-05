import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { tagsApi } from '@/api/tags';
import { CreateTagData, UpdateTagData } from '@/types/contact';

export const useTags = () => {
  const queryClient = useQueryClient();

  const { data: tags = [], isLoading, error } = useQuery({
    queryKey: ['tags'],
    queryFn: tagsApi.getTags,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const createMutation = useMutation({
    mutationFn: tagsApi.createTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
      toast.success('Tag created successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create tag');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTagData }) =>
      tagsApi.updateTag(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
      toast.success('Tag updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update tag');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: tagsApi.deleteTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
      toast.success('Tag deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete tag');
    },
  });

  return {
    tags,
    isLoading,
    error,
    createTag: (data: CreateTagData) => createMutation.mutate(data),
    updateTag: (id: string, data: UpdateTagData) => updateMutation.mutate({ id, data }),
    deleteTag: (id: string) => deleteMutation.mutate(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
