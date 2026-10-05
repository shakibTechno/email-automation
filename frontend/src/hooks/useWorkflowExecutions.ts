import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { workflowsApi } from '@/api/workflows';
import { WorkflowExecutionFilters } from '@/types/workflow';
import { PaginationParams } from '@/types/api';

// Query keys
export const executionKeys = {
  all: ['workflow-executions'] as const,
  lists: () => [...executionKeys.all, 'list'] as const,
  list: (filters?: WorkflowExecutionFilters & PaginationParams) =>
    [...executionKeys.lists(), filters] as const,
  details: () => [...executionKeys.all, 'detail'] as const,
  detail: (id: string) => [...executionKeys.details(), id] as const,
};

// Hook to list all executions
export function useWorkflowExecutions(
  params?: WorkflowExecutionFilters & PaginationParams
) {
  return useQuery({
    queryKey: executionKeys.list(params),
    queryFn: () => workflowsApi.getExecutions(params),
  });
}

// Hook to get a single execution
export function useWorkflowExecution(id: string | undefined) {
  return useQuery({
    queryKey: executionKeys.detail(id!),
    queryFn: () => workflowsApi.getExecution(id!),
    enabled: !!id,
  });
}

// Hook for execution mutations
export function useWorkflowExecutionMutations() {
  const queryClient = useQueryClient();

  const cancelExecution = useMutation({
    mutationFn: (id: string) => workflowsApi.cancelExecution(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: executionKeys.detail(id) });
      toast.success('Execution cancelled successfully!');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to cancel execution.');
    },
  });

  return {
    cancelExecution,
  };
}
