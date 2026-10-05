import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { workflowsApi } from '@/api/workflows';
import { WorkflowTemplateFilters } from '@/types/workflow';
import { PaginationParams } from '@/types/api';
import { workflowKeys } from './useWorkflows';

// Query keys
export const templateKeys = {
  all: ['workflow-templates'] as const,
  lists: () => [...templateKeys.all, 'list'] as const,
  list: (filters?: WorkflowTemplateFilters & PaginationParams) =>
    [...templateKeys.lists(), filters] as const,
  details: () => [...templateKeys.all, 'detail'] as const,
  detail: (id: string) => [...templateKeys.details(), id] as const,
};

// Hook to list templates
export function useWorkflowTemplates(
  params?: WorkflowTemplateFilters & PaginationParams
) {
  return useQuery({
    queryKey: templateKeys.list(params),
    queryFn: () => workflowsApi.getTemplates(params),
  });
}

// Hook to get a single template
export function useWorkflowTemplate(id: string | undefined) {
  return useQuery({
    queryKey: templateKeys.detail(id!),
    queryFn: () => workflowsApi.getTemplate(id!),
    enabled: !!id,
  });
}

// Hook for template mutations
export function useWorkflowTemplateMutations() {
  const queryClient = useQueryClient();

  const useTemplate = useMutation({
    mutationFn: (id: string) => workflowsApi.useTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      toast.success('Workflow created from template!');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create workflow from template.');
    },
  });

  return {
    useTemplate,
  };
}
