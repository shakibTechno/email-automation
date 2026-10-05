/**
 * React Query hooks for Contact Segmentation module
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as segmentsApi from '@/api/segments';
import type {
  SegmentListParams,
  SegmentContactsParams,
  CreateSegmentRequest,
  UpdateSegmentRequest,
  AddContactsRequest,
  RemoveContactsRequest,
  PreviewRulesRequest,
} from '@/types/segment';

// Query keys
export const segmentKeys = {
  all: ['segments'] as const,
  lists: () => [...segmentKeys.all, 'list'] as const,
  list: (params?: SegmentListParams) => [...segmentKeys.lists(), params] as const,
  details: () => [...segmentKeys.all, 'detail'] as const,
  detail: (id: string) => [...segmentKeys.details(), id] as const,
  contacts: (id: string) => [...segmentKeys.all, id, 'contacts'] as const,
  contactsPage: (id: string, params?: SegmentContactsParams) =>
    [...segmentKeys.contacts(id), params] as const,
  fieldDefinitions: () => [...segmentKeys.all, 'field-definitions'] as const,
  tags: () => [...segmentKeys.all, 'tags'] as const,
};

/**
 * Hook for fetching segment list
 */
export function useSegments(params?: SegmentListParams) {
  return useQuery({
    queryKey: segmentKeys.list(params),
    queryFn: () => segmentsApi.getSegments(params),
  });
}

/**
 * Hook for fetching a single segment
 */
export function useSegment(id: string) {
  return useQuery({
    queryKey: segmentKeys.detail(id),
    queryFn: () => segmentsApi.getSegment(id),
    enabled: !!id,
  });
}

/**
 * Hook for fetching segment contacts
 */
export function useSegmentContacts(id: string, params?: SegmentContactsParams) {
  return useQuery({
    queryKey: segmentKeys.contactsPage(id, params),
    queryFn: () => segmentsApi.getSegmentContacts(id, params),
    enabled: !!id,
  });
}

/**
 * Hook for fetching field definitions
 */
export function useFieldDefinitions() {
  return useQuery({
    queryKey: segmentKeys.fieldDefinitions(),
    queryFn: () => segmentsApi.getFieldDefinitions(),
    staleTime: 1000 * 60 * 60, // 1 hour - field definitions rarely change
  });
}

/**
 * Hook for fetching tag options
 */
export function useTagOptions() {
  return useQuery({
    queryKey: segmentKeys.tags(),
    queryFn: () => segmentsApi.getTagOptions(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Hook for creating a segment
 */
export function useCreateSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateSegmentRequest) => segmentsApi.createSegment(data),
    onSuccess: (segment) => {
      queryClient.invalidateQueries({ queryKey: segmentKeys.lists() });
      toast.success(`Segment "${segment.name}" created successfully`);
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to create segment';
      toast.error(message);
    },
  });
}

/**
 * Hook for updating a segment
 */
export function useUpdateSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateSegmentRequest }) =>
      segmentsApi.updateSegment(id, data),
    onSuccess: (segment) => {
      queryClient.invalidateQueries({ queryKey: segmentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: segmentKeys.detail(segment.id) });
      toast.success(`Segment "${segment.name}" updated successfully`);
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to update segment';
      toast.error(message);
    },
  });
}

/**
 * Hook for deleting a segment
 */
export function useDeleteSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => segmentsApi.deleteSegment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: segmentKeys.lists() });
      toast.success('Segment deleted successfully');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to delete segment';
      toast.error(message);
    },
  });
}

/**
 * Hook for refreshing segment count
 */
export function useRefreshSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => segmentsApi.refreshSegment(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: segmentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: segmentKeys.detail(id) });
      toast.success('Segment count refreshed');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to refresh segment';
      toast.error(message);
    },
  });
}

/**
 * Hook for duplicating a segment
 */
export function useDuplicateSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => segmentsApi.duplicateSegment(id),
    onSuccess: (segment) => {
      queryClient.invalidateQueries({ queryKey: segmentKeys.lists() });
      toast.success(`Segment duplicated as "${segment.name}"`);
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to duplicate segment';
      toast.error(message);
    },
  });
}

/**
 * Hook for adding contacts to a static segment
 */
export function useAddContactsToSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AddContactsRequest }) =>
      segmentsApi.addContactsToSegment(id, data),
    onSuccess: (result, { id }) => {
      queryClient.invalidateQueries({ queryKey: segmentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: segmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: segmentKeys.contacts(id) });
      toast.success(`Added ${result.added} contact(s) to segment`);
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to add contacts';
      toast.error(message);
    },
  });
}

/**
 * Hook for removing contacts from a static segment
 */
export function useRemoveContactsFromSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RemoveContactsRequest }) =>
      segmentsApi.removeContactsFromSegment(id, data),
    onSuccess: (result, { id }) => {
      queryClient.invalidateQueries({ queryKey: segmentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: segmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: segmentKeys.contacts(id) });
      toast.success(`Removed ${result.removed} contact(s) from segment`);
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to remove contacts';
      toast.error(message);
    },
  });
}

/**
 * Hook for exporting segment contacts
 */
export function useExportSegmentContacts() {
  return useMutation({
    mutationFn: async ({ id, name }: { id: string; name: string }) => {
      const blob = await segmentsApi.exportSegmentContacts(id);
      // Trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `segment_${name.replace(/\s+/g, '_')}_${id}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
    onSuccess: () => {
      toast.success('Segment contacts exported successfully');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to export contacts';
      toast.error(message);
    },
  });
}

/**
 * Hook for previewing rules
 */
export function usePreviewRules() {
  return useMutation({
    mutationFn: (data: PreviewRulesRequest) => segmentsApi.previewRules(data),
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to preview rules';
      toast.error(message);
    },
  });
}
