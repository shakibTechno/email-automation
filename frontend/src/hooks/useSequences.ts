import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { sequencesApi } from '@/api/sequences';
import type { CreateSequenceData, CreateStepData } from '@/types/sequence';

export function useSequences(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ['sequences', params],
    queryFn: () => sequencesApi.getSequences(params),
  });
}

export function useSequence(id: string) {
  return useQuery({
    queryKey: ['sequence', id],
    queryFn: () => sequencesApi.getSequence(id),
    enabled: !!id,
  });
}

export function useSequenceStats(id: string) {
  return useQuery({
    queryKey: ['sequence-stats', id],
    queryFn: () => sequencesApi.getSequenceStats(id),
    enabled: !!id,
  });
}

export function useSequenceEnrollments(id: string, params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ['sequence-enrollments', id, params],
    queryFn: () => sequencesApi.getSequenceEnrollments(id, params),
    enabled: !!id,
  });
}

export function useSequenceMutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['sequences'] });
  };
  const invalidateOne = (id: string) => {
    qc.invalidateQueries({ queryKey: ['sequence', id] });
    qc.invalidateQueries({ queryKey: ['sequence-stats', id] });
    qc.invalidateQueries({ queryKey: ['sequence-enrollments', id] });
  };

  const create = useMutation({
    mutationFn: (data: CreateSequenceData) => sequencesApi.createSequence(data),
    onSuccess: () => invalidate(),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CreateSequenceData> }) =>
      sequencesApi.updateSequence(id, data),
    onSuccess: (_, { id }) => { invalidate(); invalidateOne(id); },
  });

  const remove = useMutation({
    mutationFn: (id: string) => sequencesApi.deleteSequence(id),
    onSuccess: () => invalidate(),
  });

  const activate = useMutation({
    mutationFn: (id: string) => sequencesApi.activateSequence(id),
    onSuccess: (_, id) => { invalidate(); invalidateOne(id); },
  });

  const pause = useMutation({
    mutationFn: (id: string) => sequencesApi.pauseSequence(id),
    onSuccess: (_, id) => { invalidate(); invalidateOne(id); },
  });

  const duplicate = useMutation({
    mutationFn: (id: string) => sequencesApi.duplicateSequence(id),
    onSuccess: () => invalidate(),
  });

  const enroll = useMutation({
    mutationFn: ({ id, contactIds }: { id: string; contactIds: string[] }) =>
      sequencesApi.enrollContacts(id, contactIds),
    onSuccess: (_, { id }) => invalidateOne(id),
  });

  return { create, update, remove, activate, pause, duplicate, enroll };
}

export function useStepMutations(sequenceId: string) {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['sequence', sequenceId] });
  };

  // Every one of these had onSuccess and no onError, so a failed request
  // changed nothing on screen and said nothing — indistinguishable from the
  // button not being wired up, which is how long this took to pin down.
  const onError = (error: { message?: string }, fallback: string) =>
    toast.error(error?.message || fallback);

  const createStep = useMutation({
    mutationFn: (data: CreateStepData) => sequencesApi.createStep(data),
    onSuccess: () => {
      invalidate();
      toast.success('Step added.');
    },
    onError: (e: { message?: string }) => onError(e, 'Could not add that step'),
  });

  const updateStep = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CreateStepData> }) =>
      sequencesApi.updateStep(id, data),
    onSuccess: () => {
      invalidate();
      toast.success('Step saved.');
    },
    onError: (e: { message?: string }) => onError(e, 'Could not save that step'),
  });

  const deleteStep = useMutation({
    mutationFn: (id: string) => sequencesApi.deleteStep(id),
    onSuccess: () => {
      invalidate();
      toast.success('Step removed.');
    },
    onError: (e: { message?: string }) => onError(e, 'Could not remove that step'),
  });

  const reorderSteps = useMutation({
    mutationFn: (stepIds: string[]) => sequencesApi.reorderSteps(sequenceId, stepIds),
    onSuccess: () => invalidate(),
    onError: (e: { message?: string }) => onError(e, 'Could not reorder the steps'),
  });

  return { createStep, updateStep, deleteStep, reorderSteps };
}

export function useContactActivityTimeline(contactId: string, params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['contact-activity', contactId, params],
    queryFn: () => sequencesApi.getContactActivityTimeline(contactId, params),
    enabled: !!contactId,
  });
}
