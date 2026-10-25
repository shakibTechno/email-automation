import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { MutateOptions } from '@tanstack/react-query';
import { toast } from 'sonner';
import { tagsApi } from '@/api/tags';
import { Tag, CreateTagData, UpdateTagData } from '@/types/contact';

/**
 * Tag names are unique per organization, so a second "Newsletter" comes back as
 * a 400 with the message buried in a per-field array. The axios interceptor
 * only unwraps `message`/`error`/`errors`/`non_field_errors`, so without this
 * the user would see "Request failed with status code 400".
 */
const describeFailure = (error: any, fallback: string): string => {
  const fieldErrors = error?.errors;
  if (fieldErrors && typeof fieldErrors === 'object' && !Array.isArray(fieldErrors)) {
    const first = Object.values(fieldErrors).flat()[0];
    if (typeof first === 'string') return first;
  }
  if (error?.message && !/status code/i.test(error.message)) return error.message;
  return fallback;
};

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
      toast.success('Tag created');
    },
    onError: (error: any) => {
      toast.error(describeFailure(error, 'Failed to create tag'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTagData }) =>
      tagsApi.updateTag(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
      toast.success('Tag updated');
    },
    onError: (error: any) => {
      toast.error(describeFailure(error, 'Failed to update tag'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: tagsApi.deleteTag,
    onSuccess: () => {
      // A deleted tag disappears from every contact that carried it.
      queryClient.invalidateQueries({ queryKey: ['tags'] });
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      toast.success('Tag deleted');
    },
    onError: (error: any) => {
      toast.error(describeFailure(error, 'Failed to delete tag'));
    },
  });

  return {
    tags,
    isLoading,
    error,
    // The callers pass `onSuccess` so a dialog closes only once the write has
    // actually landed — closing optimistically threw away rejected names.
    createTag: (
      data: CreateTagData,
      options?: MutateOptions<Tag, unknown, CreateTagData>
    ) => createMutation.mutate(data, options),
    updateTag: (
      id: string,
      data: UpdateTagData,
      options?: MutateOptions<Tag, unknown, { id: string; data: UpdateTagData }>
    ) => updateMutation.mutate({ id, data }, options),
    deleteTag: (id: string, options?: MutateOptions<void, unknown, string>) =>
      deleteMutation.mutate(id, options),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
