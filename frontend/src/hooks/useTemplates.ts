import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { templatesApi } from '@/api/templates';
import {
  TemplateFilters,
  UpdateTemplateData,
} from '@/types/template';
import { PaginationParams } from '@/types/api';

export const useTemplates = (filters?: TemplateFilters & PaginationParams) => {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['templates', filters],
    queryFn: () => templatesApi.getTemplates(filters),
    staleTime: 30000,
  });

  const createMutation = useMutation({
    mutationFn: templatesApi.createTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      toast.success('Template created successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create template');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTemplateData }) =>
      templatesApi.updateTemplate(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      queryClient.invalidateQueries({ queryKey: ['template', variables.id] });
      toast.success('Template saved successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to save template');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: templatesApi.deleteTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      toast.success('Template deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete template');
    },
  });

  const duplicateMutation = useMutation({
    mutationFn: templatesApi.duplicateTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      toast.success('Template duplicated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to duplicate template');
    },
  });

  return {
    templates: data?.data || [],
    total: data?.total || 0,
    page: data?.page || 1,
    perPage: data?.per_page || 20,
    totalPages: data?.total_pages || 0,
    isLoading,
    error,
    createTemplate: createMutation.mutateAsync,
    updateTemplate: (id: string, data: UpdateTemplateData) =>
      updateMutation.mutateAsync({ id, data }),
    deleteTemplate: (id: string) => deleteMutation.mutate(id),
    duplicateTemplate: (id: string) => duplicateMutation.mutate(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isDuplicating: duplicateMutation.isPending,
  };
};

export const useTemplate = (id: string) => {
  const { data: template, isLoading, error } = useQuery({
    queryKey: ['template', id],
    queryFn: () => templatesApi.getTemplate(id),
    enabled: !!id,
  });

  return {
    template,
    isLoading,
    error,
  };
};
