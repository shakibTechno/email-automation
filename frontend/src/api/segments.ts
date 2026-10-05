/**
 * API client for Contact Segmentation module
 */
import apiClient from './client';
import type {
  Segment,
  SegmentListResponse,
  SegmentContactsResponse,
  CreateSegmentRequest,
  UpdateSegmentRequest,
  AddContactsRequest,
  RemoveContactsRequest,
  AddContactsResponse,
  RemoveContactsResponse,
  RefreshResponse,
  PreviewRulesRequest,
  PreviewResult,
  FieldDefinition,
  TagOption,
  SegmentListParams,
  SegmentContactsParams,
} from '@/types/segment';

const BASE_URL = '/segments';

/**
 * Get list of segments with optional filters
 */
export async function getSegments(params?: SegmentListParams): Promise<SegmentListResponse> {
  const response = await apiClient.get<SegmentListResponse>(BASE_URL, { params });
  return response.data;
}

/**
 * Get a single segment by ID
 */
export async function getSegment(id: string): Promise<Segment> {
  const response = await apiClient.get<Segment>(`${BASE_URL}/${id}`);
  return response.data;
}

/**
 * Create a new segment
 */
export async function createSegment(data: CreateSegmentRequest): Promise<Segment> {
  const response = await apiClient.post<Segment>(BASE_URL, data);
  return response.data;
}

/**
 * Update an existing segment
 */
export async function updateSegment(id: string, data: UpdateSegmentRequest): Promise<Segment> {
  const response = await apiClient.patch<Segment>(`${BASE_URL}/${id}`, data);
  return response.data;
}

/**
 * Delete a segment
 */
export async function deleteSegment(id: string): Promise<void> {
  await apiClient.delete(`${BASE_URL}/${id}`);
}

/**
 * Refresh segment contact count
 */
export async function refreshSegment(id: string): Promise<RefreshResponse> {
  const response = await apiClient.post<RefreshResponse>(`${BASE_URL}/${id}/refresh`);
  return response.data;
}

/**
 * Duplicate a segment
 */
export async function duplicateSegment(id: string): Promise<Segment> {
  const response = await apiClient.post<Segment>(`${BASE_URL}/${id}/duplicate`);
  return response.data;
}

/**
 * Get contacts in a segment
 */
export async function getSegmentContacts(
  id: string,
  params?: SegmentContactsParams
): Promise<SegmentContactsResponse> {
  const response = await apiClient.get<SegmentContactsResponse>(
    `${BASE_URL}/${id}/contacts`,
    { params }
  );
  return response.data;
}

/**
 * Add contacts to a static segment
 */
export async function addContactsToSegment(
  id: string,
  data: AddContactsRequest
): Promise<AddContactsResponse> {
  const response = await apiClient.post<AddContactsResponse>(
    `${BASE_URL}/${id}/add-contacts`,
    data
  );
  return response.data;
}

/**
 * Remove contacts from a static segment
 */
export async function removeContactsFromSegment(
  id: string,
  data: RemoveContactsRequest
): Promise<RemoveContactsResponse> {
  const response = await apiClient.post<RemoveContactsResponse>(
    `${BASE_URL}/${id}/remove-contacts`,
    data
  );
  return response.data;
}

/**
 * Export segment contacts as CSV
 */
export async function exportSegmentContacts(id: string): Promise<Blob> {
  const response = await apiClient.get(`${BASE_URL}/${id}/export`, {
    responseType: 'blob',
  });
  return response.data;
}

/**
 * Preview rules without saving
 */
export async function previewRules(data: PreviewRulesRequest): Promise<PreviewResult> {
  const response = await apiClient.post<PreviewResult>(`${BASE_URL}/preview`, data);
  return response.data;
}

/**
 * Get available field definitions for segment builder
 */
export async function getFieldDefinitions(): Promise<FieldDefinition[]> {
  const response = await apiClient.get<FieldDefinition[]>(`${BASE_URL}/field-definitions`);
  return response.data;
}

/**
 * Get available tags for tag field
 */
export async function getTagOptions(): Promise<TagOption[]> {
  const response = await apiClient.get<TagOption[]>(`${BASE_URL}/tags`);
  return response.data;
}
