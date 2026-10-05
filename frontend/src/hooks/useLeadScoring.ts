import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as api from '@/api/leadScoring';
import type {
  ScoringRuleFormData,
  ScoringRuleListParams,
  ScoreThresholdInput,
} from '@/types/leadScoring';

export const scoringKeys = {
  all: ['lead-scoring'] as const,
  rules: (params?: ScoringRuleListParams) => [...scoringKeys.all, 'rules', params] as const,
  thresholds: () => [...scoringKeys.all, 'thresholds'] as const,
};

export function useScoringRules(params?: ScoringRuleListParams) {
  return useQuery({
    queryKey: scoringKeys.rules(params),
    queryFn: () => api.getScoringRules(params),
  });
}

export function useScoreThresholds() {
  return useQuery({
    queryKey: scoringKeys.thresholds(),
    queryFn: () => api.getScoreThresholds(),
    staleTime: 1000 * 60 * 5,
  });
}

export function useCreateScoringRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ScoringRuleFormData) => api.createScoringRule(data),
    onSuccess: (rule) => {
      qc.invalidateQueries({ queryKey: scoringKeys.all });
      toast.success(`Rule "${rule.name}" created`);
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.detail || 'Failed to create rule');
    },
  });
}

export function useUpdateScoringRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ScoringRuleFormData> }) =>
      api.updateScoringRule(id, data),
    onSuccess: (rule) => {
      qc.invalidateQueries({ queryKey: scoringKeys.all });
      toast.success(`Rule "${rule.name}" updated`);
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.detail || 'Failed to update rule');
    },
  });
}

export function useDeleteScoringRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteScoringRule(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scoringKeys.all });
      toast.success('Rule deleted');
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.detail || 'Failed to delete rule');
    },
  });
}

export function useToggleScoringRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.toggleScoringRule(id),
    onSuccess: (rule) => {
      qc.invalidateQueries({ queryKey: scoringKeys.all });
      toast.success(`Rule "${rule.name}" ${rule.is_active ? 'enabled' : 'disabled'}`);
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.detail || 'Failed to toggle rule');
    },
  });
}

export function useBulkUpdateThresholds() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (thresholds: ScoreThresholdInput[]) =>
      api.bulkUpdateThresholds(thresholds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scoringKeys.thresholds() });
      toast.success('Score thresholds saved');
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.detail || 'Failed to save thresholds');
    },
  });
}
