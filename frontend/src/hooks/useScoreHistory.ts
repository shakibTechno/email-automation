import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as api from '@/api/leadScoring';

export const scoreHistoryKeys = {
  all: ['score-history'] as const,
  contact: (id: string) => [...scoreHistoryKeys.all, id] as const,
  page: (id: string, params?: object) => [...scoreHistoryKeys.contact(id), params] as const,
};

export function useScoreHistory(contactId: string, params?: { page?: number }) {
  return useQuery({
    queryKey: scoreHistoryKeys.page(contactId, params),
    queryFn: () => api.getScoreHistory(contactId, params),
    enabled: !!contactId,
  });
}

export function useAdjustScore(contactId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { points_delta: number; note?: string }) =>
      api.adjustScore(contactId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scoreHistoryKeys.contact(contactId) });
      qc.invalidateQueries({ queryKey: ['contacts', contactId] });
      toast.success('Score adjusted');
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.detail || 'Failed to adjust score');
    },
  });
}

export function useRecalculateScore(contactId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.recalculateScore(contactId),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: scoreHistoryKeys.contact(contactId) });
      qc.invalidateQueries({ queryKey: ['contacts', contactId] });
      toast.success(`Score recalculated: ${data.lead_score}`);
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.detail || 'Failed to recalculate score');
    },
  });
}

export function usePreviewScore(contactId: string) {
  return useQuery({
    queryKey: [...scoreHistoryKeys.contact(contactId), 'preview'],
    queryFn: () => api.previewScore(contactId),
    enabled: !!contactId,
  });
}
