import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { crmApi } from '@/api/crm';
import {
  DealFilters,
  ActivityFilters,
  UpdateDealData,
  UpdateActivityData,
  UpdatePipelineData,
  KanbanStage,
  CreateTaskData,
  UpdateTaskData,
  TaskFilters,
  CompanyFilters,
  CreateCompanyData,
  UpdateCompanyData,
} from '@/types/crm';
import { PaginationParams } from '@/types/api';

// ── Pipelines ──

export const usePipelines = () => {
  return useQuery({
    queryKey: ['pipelines'],
    queryFn: crmApi.getPipelines,
    staleTime: 60000,
  });
};

export const usePipeline = (id: string) => {
  return useQuery({
    queryKey: ['pipeline', id],
    queryFn: () => crmApi.getPipeline(id),
    enabled: !!id,
  });
};

export const usePipelineMutations = () => {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: crmApi.createPipeline,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Pipeline created successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create pipeline');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdatePipelineData }) =>
      crmApi.updatePipeline(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      queryClient.invalidateQueries({ queryKey: ['pipeline', variables.id] });
      toast.success('Pipeline updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update pipeline');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: crmApi.deletePipeline,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Pipeline deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete pipeline');
    },
  });

  const addStageMutation = useMutation({
    mutationFn: ({ pipelineId, data }: {
      pipelineId: string;
      data: { name: string; color?: string; stage_type?: string; default_probability?: number };
    }) => crmApi.addStage(pipelineId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pipeline', variables.pipelineId] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      toast.success('Stage added successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to add stage');
    },
  });

  const removeStageMutation = useMutation({
    mutationFn: ({ pipelineId, stageId }: { pipelineId: string; stageId: string }) =>
      crmApi.removeStage(pipelineId, stageId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pipeline', variables.pipelineId] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      toast.success('Stage removed successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to remove stage');
    },
  });

  const reorderStagesMutation = useMutation({
    mutationFn: ({ pipelineId, stageIds }: { pipelineId: string; stageIds: string[] }) =>
      crmApi.reorderStages(pipelineId, stageIds),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pipeline', variables.pipelineId] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to reorder stages');
    },
  });

  return {
    createPipeline: createMutation.mutateAsync,
    updatePipeline: (id: string, data: UpdatePipelineData) =>
      updateMutation.mutateAsync({ id, data }),
    deletePipeline: (id: string) => deleteMutation.mutateAsync(id),
    addStage: (pipelineId: string, data: { name: string; color?: string; stage_type?: string; default_probability?: number }) =>
      addStageMutation.mutateAsync({ pipelineId, data }),
    removeStage: (pipelineId: string, stageId: string) =>
      removeStageMutation.mutateAsync({ pipelineId, stageId }),
    reorderStages: (pipelineId: string, stageIds: string[]) =>
      reorderStagesMutation.mutateAsync({ pipelineId, stageIds }),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};

// ── Kanban ──

export const useKanban = (pipelineId: string) => {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['kanban', pipelineId],
    queryFn: () => crmApi.getKanbanData(pipelineId),
    enabled: !!pipelineId,
    staleTime: 15000,
  });

  const moveMutation = useMutation({
    mutationFn: ({ dealId, stageId, position }: {
      dealId: string;
      stageId: string;
      position?: number;
    }) => crmApi.moveDeal(dealId, stageId, position),
    onMutate: async ({ dealId, stageId, position }) => {
      // Optimistic update for instant drag feedback
      await queryClient.cancelQueries({ queryKey: ['kanban', pipelineId] });
      const previous = queryClient.getQueryData<KanbanStage[]>(['kanban', pipelineId]);

      if (previous) {
        const updated = previous.map(col => ({
          ...col,
          deals: col.deals.filter(d => d.id !== dealId),
          deal_count: col.deals.filter(d => d.id !== dealId).length,
        }));

        // Find the deal card
        let movedDeal = null;
        for (const col of previous) {
          const found = col.deals.find(d => d.id === dealId);
          if (found) {
            movedDeal = found;
            break;
          }
        }

        if (movedDeal) {
          const targetCol = updated.find(col => col.stage.id === stageId);
          if (targetCol) {
            const insertAt = position !== undefined ? position : targetCol.deals.length;
            targetCol.deals.splice(insertAt, 0, { ...movedDeal, position: insertAt });
            targetCol.deal_count = targetCol.deals.length;
          }
        }

        queryClient.setQueryData(['kanban', pipelineId], updated);
      }

      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(['kanban', pipelineId], context.previous);
      }
      toast.error('Failed to move deal');
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['kanban', pipelineId] });
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      queryClient.invalidateQueries({ queryKey: ['deals'] });
    },
  });

  return {
    kanbanData: data || [],
    isLoading,
    error,
    moveDeal: (dealId: string, stageId: string, position?: number) =>
      moveMutation.mutate({ dealId, stageId, position }),
    isMoving: moveMutation.isPending,
  };
};

// ── Deals ──

export const useDeals = (filters?: DealFilters & PaginationParams) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['deals', filters],
    queryFn: () => crmApi.getDeals(filters),
    staleTime: 30000,
  });

  return {
    deals: data?.data || [],
    total: data?.total || 0,
    page: data?.page || 1,
    perPage: data?.per_page || 20,
    totalPages: data?.total_pages || 0,
    isLoading,
    error,
  };
};

export const useDeal = (id: string) => {
  return useQuery({
    queryKey: ['deal', id],
    queryFn: () => crmApi.getDeal(id),
    enabled: !!id,
  });
};

export const useDealMutations = () => {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: crmApi.createDeal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Deal created successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create deal');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateDealData }) =>
      crmApi.updateDeal(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['deal', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      toast.success('Deal updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update deal');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: crmApi.deleteDeal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Deal deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete deal');
    },
  });

  const winMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      crmApi.winDeal(id, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['deal', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Deal marked as won!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update deal');
    },
  });

  const loseMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      crmApi.loseDeal(id, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['deal', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Deal marked as lost.');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update deal');
    },
  });

  const reopenMutation = useMutation({
    mutationFn: ({ id, stageId }: { id: string; stageId?: string }) =>
      crmApi.reopenDeal(id, stageId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['deal', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Deal reopened!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to reopen deal');
    },
  });

  const addContactMutation = useMutation({
    mutationFn: ({ dealId, data }: {
      dealId: string;
      data: { contact_id: string; role?: string; is_primary?: boolean };
    }) => crmApi.addDealContact(dealId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['deal', variables.dealId] });
      toast.success('Contact added to deal!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to add contact');
    },
  });

  const removeContactMutation = useMutation({
    mutationFn: ({ dealId, contactId }: { dealId: string; contactId: string }) =>
      crmApi.removeDealContact(dealId, contactId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['deal', variables.dealId] });
      toast.success('Contact removed from deal.');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to remove contact');
    },
  });

  return {
    createDeal: createMutation.mutateAsync,
    updateDeal: (id: string, data: UpdateDealData) => updateMutation.mutateAsync({ id, data }),
    deleteDeal: (id: string) => deleteMutation.mutateAsync(id),
    winDeal: (id: string, reason?: string) => winMutation.mutateAsync({ id, reason }),
    loseDeal: (id: string, reason?: string) => loseMutation.mutateAsync({ id, reason }),
    reopenDeal: (id: string, stageId?: string) => reopenMutation.mutateAsync({ id, stageId }),
    addContact: (dealId: string, data: { contact_id: string; role?: string; is_primary?: boolean }) =>
      addContactMutation.mutateAsync({ dealId, data }),
    removeContact: (dealId: string, contactId: string) =>
      removeContactMutation.mutateAsync({ dealId, contactId }),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isWinning: winMutation.isPending,
    isLosing: loseMutation.isPending,
  };
};

// ── Activities ──

export const useActivities = (filters?: ActivityFilters & PaginationParams) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['activities', filters],
    queryFn: () => crmApi.getActivities(filters),
    staleTime: 30000,
  });

  return {
    activities: data?.data || [],
    total: data?.total || 0,
    page: data?.page || 1,
    perPage: data?.per_page || 20,
    totalPages: data?.total_pages || 0,
    isLoading,
    error,
  };
};

export const useActivityMutations = () => {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: crmApi.createActivity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] });
      queryClient.invalidateQueries({ queryKey: ['deal'] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      toast.success('Activity logged successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create activity');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateActivityData }) =>
      crmApi.updateActivity(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] });
      queryClient.invalidateQueries({ queryKey: ['deal'] });
      toast.success('Activity updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update activity');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: crmApi.deleteActivity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] });
      queryClient.invalidateQueries({ queryKey: ['deal'] });
      toast.success('Activity deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete activity');
    },
  });

  const completeMutation = useMutation({
    mutationFn: crmApi.completeActivity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] });
      queryClient.invalidateQueries({ queryKey: ['deal'] });
      queryClient.invalidateQueries({ queryKey: ['kanban'] });
      toast.success('Activity completed!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to complete activity');
    },
  });

  return {
    createActivity: createMutation.mutateAsync,
    updateActivity: (id: string, data: UpdateActivityData) =>
      updateMutation.mutateAsync({ id, data }),
    deleteActivity: (id: string) => deleteMutation.mutateAsync(id),
    completeActivity: (id: string) => completeMutation.mutateAsync(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};

// ── Pipeline Analytics ──

export const usePipelineAnalytics = (pipelineId: string, days?: number) => {
  return useQuery({
    queryKey: ['pipeline-analytics', pipelineId, days],
    queryFn: () => crmApi.getPipelineAnalytics(pipelineId, days),
    enabled: !!pipelineId,
    staleTime: 60000,
  });
};

// ── Contact integration ──

export const useContactDeals = (contactId: string) => {
  return useQuery({
    queryKey: ['contact-deals', contactId],
    queryFn: () => crmApi.getContactDeals(contactId),
    enabled: !!contactId,
    staleTime: 30000,
  });
};

// ── CRM Tasks ──

export const useTasks = (filters?: TaskFilters & PaginationParams) => {
  return useQuery({
    queryKey: ['crm-tasks', filters],
    queryFn: () => crmApi.getTasks(filters),
    staleTime: 30000,
  });
};

export const useTaskMutations = () => {
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['crm-tasks'] });
    queryClient.invalidateQueries({ queryKey: ['deal'] });
  };

  const createMutation = useMutation({
    mutationFn: (data: CreateTaskData) => crmApi.createTask(data),
    onSuccess: () => { invalidate(); toast.success('Task created!'); },
    onError: (e: any) => toast.error(e.message || 'Failed to create task'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTaskData }) => crmApi.updateTask(id, data),
    onSuccess: () => { invalidate(); toast.success('Task updated!'); },
    onError: (e: any) => toast.error(e.message || 'Failed to update task'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => crmApi.deleteTask(id),
    onSuccess: () => { invalidate(); toast.success('Task deleted.'); },
    onError: (e: any) => toast.error(e.message || 'Failed to delete task'),
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => crmApi.completeTask(id),
    onSuccess: () => { invalidate(); toast.success('Task completed!'); },
    onError: (e: any) => toast.error(e.message || 'Failed to complete task'),
  });

  return {
    createTask: (data: CreateTaskData) => createMutation.mutateAsync(data),
    updateTask: (id: string, data: UpdateTaskData) => updateMutation.mutateAsync({ id, data }),
    deleteTask: (id: string) => deleteMutation.mutateAsync(id),
    completeTask: (id: string) => completeMutation.mutateAsync(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
  };
};

// ── Revenue Forecasting ──

export const useForecast = () => {
  return useQuery({
    queryKey: ['crm-forecast'],
    queryFn: crmApi.getForecast,
    staleTime: 60000,
  });
};

// ── Companies ──

export const useCompanies = (filters?: CompanyFilters) => {
  return useQuery({
    queryKey: ['companies', filters],
    queryFn: () => crmApi.getCompanies(filters),
    staleTime: 30000,
  });
};

export const useCompany = (id: string) => {
  return useQuery({
    queryKey: ['company', id],
    queryFn: () => crmApi.getCompany(id),
    enabled: !!id,
  });
};

export const useCompanyContacts = (id: string) => {
  return useQuery({
    queryKey: ['company-contacts', id],
    queryFn: () => crmApi.getCompanyContacts(id),
    enabled: !!id,
  });
};

export const useCompanyDeals = (id: string) => {
  return useQuery({
    queryKey: ['company-deals', id],
    queryFn: () => crmApi.getCompanyDeals(id),
    enabled: !!id,
  });
};

export const useCompanyActivities = (id: string) => {
  return useQuery({
    queryKey: ['company-activities', id],
    queryFn: () => crmApi.getCompanyActivities(id),
    enabled: !!id,
  });
};

export const useCompanyMutations = () => {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: CreateCompanyData) => crmApi.createCompany(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      toast.success('Company created successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.name?.[0] || error.message || 'Failed to create company');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCompanyData }) =>
      crmApi.updateCompany(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['company', variables.id] });
      toast.success('Company updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update company');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => crmApi.deleteCompany(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      toast.success('Company deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete company');
    },
  });

  return {
    createCompany: (data: CreateCompanyData) => createMutation.mutateAsync(data),
    updateCompany: (id: string, data: UpdateCompanyData) =>
      updateMutation.mutateAsync({ id, data }),
    deleteCompany: (id: string) => deleteMutation.mutateAsync(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
