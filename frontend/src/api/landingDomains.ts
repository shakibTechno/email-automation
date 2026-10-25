import apiClient from './client';
import type { LandingDomain } from '@/types/landing-page';

const BASE_URL = '/landing-domains';

interface Paginated<T> {
  results: T[];
  count: number;
}

export async function listDomains(): Promise<LandingDomain[]> {
  const { data } = await apiClient.get<Paginated<LandingDomain>>(BASE_URL);
  return data.results ?? [];
}

export async function connectDomain(domain: string): Promise<LandingDomain> {
  const { data } = await apiClient.post<LandingDomain>(BASE_URL, { domain });
  return data;
}

/**
 * Check a domain now. Resolves even when the domain is not ready — "your DNS
 * has not propagated" is an answer, and it arrives in `last_check_error`.
 */
export async function verifyDomain(id: string): Promise<LandingDomain> {
  const { data } = await apiClient.post<LandingDomain>(`${BASE_URL}/${id}/verify`, {});
  return data;
}

export async function setPrimaryDomain(id: string): Promise<LandingDomain> {
  const { data } = await apiClient.post<LandingDomain>(`${BASE_URL}/${id}/set-primary`, {});
  return data;
}

export async function disconnectDomain(id: string): Promise<void> {
  await apiClient.delete(`${BASE_URL}/${id}`);
}
