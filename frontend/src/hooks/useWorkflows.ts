import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { workflowsApi } from '@/api/workflows';
import {
  WorkflowFilters,
  WorkflowExecutionFilters,
  CreateWorkflowData,
  UpdateWorkflowData,
} from '@/types/workflow';
import { PaginationParams } from '@/types/api';

// Query keys
export const workflowKeys = {
  all: ['workflows'] as const,
  lists: () => [...workflowKeys.all, 'list'] as const,
  list: (filters?: WorkflowFilters & PaginationParams) =>
    [...workflowKeys.lists(), filters] as const,
  details: () => [...workflowKeys.all, 'detail'] as const,
  detail: (id: string) => [...workflowKeys.details(), id] as const,
  analytics: (id: string, days?: number) =>
    [...workflowKeys.detail(id), 'analytics', days] as const,
  executions: (id: string, filters?: WorkflowExecutionFilters & PaginationParams) =>
    [...workflowKeys.detail(id), 'executions', filters] as const,
  validation: (id: string) => [...workflowKeys.detail(id), 'validation'] as const,
};

// Hook to list workflows
export function useWorkflows(params?: WorkflowFilters & PaginationParams) {
  return useQuery({
    queryKey: workflowKeys.list(params),
    queryFn: () => workflowsApi.getWorkflows(params),
  });
}

// Hook to get a single workflow
export function useWorkflow(id: string | undefined) {
  return useQuery({
    queryKey: workflowKeys.detail(id!),
    queryFn: () => workflowsApi.getWorkflow(id!),
    enabled: !!id,
  });
}

// Hook to get workflow analytics
export function useWorkflowAnalytics(id: string | undefined, days = 30) {
  return useQuery({
    queryKey: workflowKeys.analytics(id!, days),
    queryFn: () => workflowsApi.getWorkflowAnalytics(id!, days),
    enabled: !!id,
  });
}

// Hook to get workflow executions
export function useWorkflowExecutions(
  id: string | undefined,
  params?: WorkflowExecutionFilters & PaginationParams
) {
  return useQuery({
    queryKey: workflowKeys.executions(id!, params),
    queryFn: () => workflowsApi.getWorkflowExecutions(id!, params),
    enabled: !!id,
    refetchInterval: (query) => {
      const items = query.state.data?.data ?? [];
      return items.some((e) => e.status === 'active' || e.status === 'waiting') ? 5000 : false;
    },
  });
}

// Hook to validate a workflow
export function useWorkflowValidation(id: string | undefined) {
  return useQuery({
    queryKey: workflowKeys.validation(id!),
    queryFn: () => workflowsApi.validateWorkflow(id!),
    enabled: !!id,
  });
}

// Hook for workflow mutations
export function useWorkflowMutations() {
  const queryClient = useQueryClient();

  const createWorkflow = useMutation({
    mutationFn: (data: CreateWorkflowData) => workflowsApi.createWorkflow(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      toast.success('Workflow created successfully!');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create workflow.');
    },
  });

  const updateWorkflow = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateWorkflowData }) =>
      workflowsApi.updateWorkflow(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(id) });
      toast.success('Workflow saved successfully!');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to save workflow.');
    },
  });

  const deleteWorkflow = useMutation({
    mutationFn: (id: string) => workflowsApi.deleteWorkflow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      toast.success('Workflow deleted successfully!');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete workflow.');
    },
  });

  const activateWorkflow = useMutation({
    mutationFn: (id: string) => workflowsApi.activateWorkflow(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(id) });
      toast.success('Workflow activated! It will now trigger automatically.');
    },
    onError: (error: Error & { response?: { data?: { errors?: string[] } } }) => {
      const errors = error.response?.data?.errors;
      toast.error(errors?.join(', ') || error.message || 'Failed to activate workflow.');
    },
  });

  const deactivateWorkflow = useMutation({
    mutationFn: (id: string) => workflowsApi.deactivateWorkflow(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(id) });
      toast.success('Workflow paused successfully!');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to pause workflow.');
    },
  });

  const duplicateWorkflow = useMutation({
    mutationFn: (id: string) => workflowsApi.duplicateWorkflow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      toast.success('Workflow duplicated successfully!');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to duplicate workflow.');
    },
  });

  return {
    createWorkflow,
    updateWorkflow,
    deleteWorkflow,
    activateWorkflow,
    deactivateWorkflow,
    duplicateWorkflow,
  };
}
