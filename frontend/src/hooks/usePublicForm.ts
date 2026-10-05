import { useMutation, useQuery } from '@tanstack/react-query';
import { formsApi } from '@/api/forms';
import { PublicFormData } from '@/types/form';

export const usePublicForm = (id: string) => {
  const { data: form, isLoading, error } = useQuery({
    queryKey: ['public-form', id],
    queryFn: () => formsApi.getPublicForm(id),
    enabled: !!id,
    retry: false,
  });

  return {
    form,
    isLoading,
    error,
  };
};

export const useSubmitForm = (id: string) => {
  const mutation = useMutation({
    mutationFn: (data: PublicFormData) => formsApi.submitPublicForm(id, data),
  });

  return {
    submitForm: mutation.mutateAsync,
    isSubmitting: mutation.isPending,
    isSuccess: mutation.isSuccess,
    data: mutation.data,
    error: mutation.error,
    reset: mutation.reset,
  };
};
