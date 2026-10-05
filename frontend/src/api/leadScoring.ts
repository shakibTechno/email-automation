import apiClient from './client';
import type {
  ScoringRule,
  ScoringRuleFormData,
  ScoringRuleListParams,
  ScoreThreshold,
  ScoreThresholdInput,
  ScoreHistoryEntry,
  ScorePreview,
  PaginatedResponse,
} from '@/types/leadScoring';

const RULES_URL = '/scoring-rules';
const THRESHOLDS_URL = '/score-thresholds';

// ── Scoring Rules ────────────────────────────────────────────────────────────

export async function getScoringRules(
  params?: ScoringRuleListParams
): Promise<PaginatedResponse<ScoringRule>> {
  const res = await apiClient.get<PaginatedResponse<ScoringRule>>(RULES_URL, { params });
  return res.data;
}

export async function createScoringRule(data: ScoringRuleFormData): Promise<ScoringRule> {
  const res = await apiClient.post<ScoringRule>(RULES_URL, data);
  return res.data;
}

export async function updateScoringRule(
  id: string,
  data: Partial<ScoringRuleFormData>
): Promise<ScoringRule> {
  const res = await apiClient.patch<ScoringRule>(`${RULES_URL}/${id}`, data);
  return res.data;
}

export async function deleteScoringRule(id: string): Promise<void> {
  await apiClient.delete(`${RULES_URL}/${id}`);
}

export async function toggleScoringRule(id: string): Promise<ScoringRule> {
  const res = await apiClient.post<ScoringRule>(`${RULES_URL}/${id}/toggle`);
  return res.data;
}

export async function reorderScoringRules(orderedIds: string[]): Promise<void> {
  await apiClient.post(`${RULES_URL}/reorder`, { ordered_ids: orderedIds });
}

// ── Score Thresholds ─────────────────────────────────────────────────────────

export async function getScoreThresholds(): Promise<ScoreThreshold[]> {
  const res = await apiClient.get<PaginatedResponse<ScoreThreshold>>(THRESHOLDS_URL);
  return res.data.results;
}

export async function bulkUpdateThresholds(
  thresholds: ScoreThresholdInput[]
): Promise<ScoreThreshold[]> {
  const res = await apiClient.post<ScoreThreshold[]>(
    `${THRESHOLDS_URL}/bulk-update`,
    { thresholds }
  );
  return res.data;
}

// ── Contact score actions (scoped to contacts router) ────────────────────────

export async function getScoreHistory(
  contactId: string,
  params?: { page?: number }
): Promise<PaginatedResponse<ScoreHistoryEntry>> {
  const res = await apiClient.get<PaginatedResponse<ScoreHistoryEntry>>(
    `/contacts/${contactId}/score-history`,
    { params }
  );
  return res.data;
}

export async function adjustScore(
  contactId: string,
  data: { points_delta: number; note?: string }
): Promise<{ lead_score: number; engagement_level: string }> {
  const res = await apiClient.post(`/contacts/${contactId}/adjust-score`, data);
  return res.data;
}

export async function recalculateScore(
  contactId: string
): Promise<{ lead_score: number; engagement_level: string }> {
  const res = await apiClient.post(`/contacts/${contactId}/recalculate-score`, {});
  return res.data;
}

export async function previewScore(contactId: string): Promise<ScorePreview> {
  const res = await apiClient.get<ScorePreview>(
    `/contacts/${contactId}/preview-score`
  );
  return res.data;
}
