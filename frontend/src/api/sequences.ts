import apiClient from './client';
import type {
  EmailSequence,
  EmailSequenceListItem,
  CreateSequenceData,
  SequenceStep,
  CreateStepData,
  SequenceEnrollment,
  SequenceStepExecution,
  SequenceStats,
  ActivityTimeline,
} from '@/types/sequence';

interface PaginatedResponse<T> {
  results: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

export const sequencesApi = {
  // Sequences
  getSequences: async (params?: Record<string, unknown>): Promise<PaginatedResponse<EmailSequenceListItem>> => {
    const { data } = await apiClient.get('/sequences', { params });
    return data;
  },

  getSequence: async (id: string): Promise<EmailSequence> => {
    const { data } = await apiClient.get(`/sequences/${id}`);
    return data;
  },

  createSequence: async (payload: CreateSequenceData): Promise<EmailSequence> => {
    const { data } = await apiClient.post('/sequences', payload);
    return data;
  },

  updateSequence: async (id: string, payload: Partial<CreateSequenceData>): Promise<EmailSequence> => {
    const { data } = await apiClient.patch(`/sequences/${id}`, payload);
    return data;
  },

  deleteSequence: async (id: string): Promise<void> => {
    await apiClient.delete(`/sequences/${id}`);
  },

  activateSequence: async (id: string): Promise<EmailSequence> => {
    const { data } = await apiClient.post(`/sequences/${id}/activate`);
    return data;
  },

  pauseSequence: async (id: string): Promise<EmailSequence> => {
    const { data } = await apiClient.post(`/sequences/${id}/pause`);
    return data;
  },

  duplicateSequence: async (id: string): Promise<EmailSequence> => {
    const { data } = await apiClient.post(`/sequences/${id}/duplicate`);
    return data;
  },

  enrollContacts: async (id: string, contactIds: string[]): Promise<{ enrolled: number; errors: unknown[] }> => {
    const { data } = await apiClient.post(`/sequences/${id}/enroll`, { contact_ids: contactIds });
    return data;
  },

  getSequenceEnrollments: async (id: string, params?: Record<string, unknown>): Promise<SequenceEnrollment[]> => {
    const { data } = await apiClient.get(`/sequences/${id}/enrollments`, { params });
    return data;
  },

  getSequenceStats: async (id: string): Promise<SequenceStats> => {
    const { data } = await apiClient.get(`/sequences/${id}/stats`);
    return data;
  },

  // Steps
  createStep: async (payload: CreateStepData): Promise<SequenceStep> => {
    const { data } = await apiClient.post('/sequence-steps', payload);
    return data;
  },

  updateStep: async (id: string, payload: Partial<CreateStepData>): Promise<SequenceStep> => {
    const { data } = await apiClient.patch(`/sequence-steps/${id}`, payload);
    return data;
  },

  deleteStep: async (id: string): Promise<void> => {
    await apiClient.delete(`/sequence-steps/${id}`);
  },

  reorderSteps: async (sequenceId: string, stepIds: string[]): Promise<void> => {
    await apiClient.post('/sequence-steps/reorder', { sequence_id: sequenceId, step_ids: stepIds });
  },

  // Enrollments
  cancelEnrollment: async (id: string): Promise<void> => {
    await apiClient.post(`/sequence-enrollments/${id}/cancel`);
  },

  getEnrollmentSteps: async (id: string): Promise<SequenceStepExecution[]> => {
    const { data } = await apiClient.get(`/sequence-enrollments/${id}/steps`);
    return data;
  },

  // Contact activity timeline
  getContactActivityTimeline: async (contactId: string, params?: { limit?: number; offset?: number }): Promise<ActivityTimeline> => {
    const { data } = await apiClient.get(`/contacts/${contactId}/activity-timeline`, { params });
    return data;
  },
};
