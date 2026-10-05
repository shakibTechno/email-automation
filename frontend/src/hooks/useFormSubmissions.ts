import { useMutation, useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { formsApi } from '@/api/forms';
import { PaginationParams } from '@/types/api';

export const useFormSubmissions = (formId: string, params?: PaginationParams) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['form-submissions', formId, params],
    queryFn: () => formsApi.getFormSubmissions(formId, params),
    enabled: !!formId,
    staleTime: 30000,
  });

  return {
    submissions: data?.data || [],
    total: data?.total || 0,
    page: data?.page || 1,
    perPage: data?.per_page || 20,
    totalPages: data?.total_pages || 0,
    isLoading,
    error,
  };
};

export const useSubmissionDetail = (formId: string, submissionId: string) => {
  const { data: submission, isLoading, error } = useQuery({
    queryKey: ['form-submission', formId, submissionId],
    queryFn: () => formsApi.getSubmissionDetail(formId, submissionId),
    enabled: !!formId && !!submissionId,
  });

  return {
    submission,
    isLoading,
    error,
  };
};

export const useExportSubmissions = () => {
  const mutation = useMutation({
    mutationFn: (formId: string) => formsApi.exportSubmissions(formId),
    onSuccess: (blob, formId) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `form_${formId}_submissions.csv`;
      link.click();
      URL.revokeObjectURL(url);
      toast.success('Submissions exported!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to export submissions');
    },
  });

  return {
    exportSubmissions: mutation.mutate,
    isExporting: mutation.isPending,
  };
};
