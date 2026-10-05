import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { formsApi } from '@/api/forms';
import { FormFilters, UpdateFormData } from '@/types/form';
import { PaginationParams } from '@/types/api';

export const useForms = (filters?: FormFilters & PaginationParams) => {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['forms', filters],
    queryFn: () => formsApi.getForms(filters),
    staleTime: 30000,
  });

  const createMutation = useMutation({
    mutationFn: formsApi.createForm,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forms'] });
      toast.success('Form created successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create form');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateFormData }) =>
      formsApi.updateForm(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['forms'] });
      queryClient.invalidateQueries({ queryKey: ['form', variables.id] });
      toast.success('Form updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update form');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: formsApi.deleteForm,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forms'] });
      toast.success('Form deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete form');
    },
  });

  const duplicateMutation = useMutation({
    mutationFn: formsApi.duplicateForm,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forms'] });
      toast.success('Form duplicated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to duplicate form');
    },
  });

  const toggleStatusMutation = useMutation({
    mutationFn: formsApi.toggleFormStatus,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['forms'] });
      queryClient.invalidateQueries({ queryKey: ['form'] });
      const msg =
        result.status === 'active'
          ? 'Form activated!'
          : 'Form deactivated.';
      toast.success(msg);
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to toggle form status');
    },
  });

  return {
    forms: data?.data || [],
    total: data?.total || 0,
    page: data?.page || 1,
    perPage: data?.per_page || 20,
    totalPages: data?.total_pages || 0,
    isLoading,
    error,
    createForm: createMutation.mutateAsync,
    updateForm: (id: string, data: UpdateFormData) =>
      updateMutation.mutateAsync({ id, data }),
    deleteForm: (id: string) => deleteMutation.mutate(id),
    duplicateForm: (id: string) => duplicateMutation.mutate(id),
    toggleFormStatus: (id: string) => toggleStatusMutation.mutate(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isDuplicating: duplicateMutation.isPending,
    isToggling: toggleStatusMutation.isPending,
  };
};

export const useForm = (id: string) => {
  const { data: form, isLoading, error } = useQuery({
    queryKey: ['form', id],
    queryFn: () => formsApi.getForm(id),
    enabled: !!id,
  });

  return {
    form,
    isLoading,
    error,
  };
};
