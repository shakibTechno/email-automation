import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { customFieldsApi } from '@/api/customFields';
import type { CustomField } from '@/types/contact';

export const customFieldKeys = {
  all: ['custom-fields'] as const,
  list: () => [...customFieldKeys.all, 'list'] as const,
};

export function useCustomFields(enabled = true) {
  const { data, isLoading, error } = useQuery({
    queryKey: customFieldKeys.list(),
    queryFn: customFieldsApi.getCustomFields,
    enabled,
    // Definitions change rarely and are read by the contact form, the detail
    // page and the segment builder, so a longer window saves a request on
    // nearly every screen.
    staleTime: 1000 * 60 * 5,
  });

  return { fields: data ?? [], isLoading, error };
}

export function useCustomFieldActions() {
  const queryClient = useQueryClient();

  // Contacts and segment field lists are invalidated too: a new definition
  // changes what the contact form renders and what the rule builder offers,
  // and a stale copy of either is a field the customer cannot see.
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: customFieldKeys.all });
    queryClient.invalidateQueries({ queryKey: ['contacts'] });
    queryClient.invalidateQueries({ queryKey: ['segments'] });
  };

  const onError = (error: { message?: string }, fallback: string) =>
    toast.error(error?.message || fallback);

  const create = useMutation({
    mutationFn: (payload: Partial<CustomField>) =>
      customFieldsApi.createCustomField(payload),
    onSuccess: (field: CustomField) => {
      invalidate();
      toast.success(`"${field.name}" added.`);
    },
    onError: (e: { message?: string }) => onError(e, 'Could not add that field'),
  });

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<CustomField> }) =>
      customFieldsApi.updateCustomField(id, payload),
    onSuccess: () => {
      invalidate();
      toast.success('Field updated.');
    },
    onError: (e: { message?: string }) => onError(e, 'Could not update that field'),
  });

  const remove = useMutation({
    mutationFn: (id: string) => customFieldsApi.deleteCustomField(id),
    onSuccess: () => {
      invalidate();
      toast.success('Field removed.');
    },
    onError: (e: { message?: string }) => onError(e, 'Could not remove that field'),
  });

  return {
    create,
    update,
    remove,
    isBusy: create.isPending || update.isPending || remove.isPending,
  };
}
