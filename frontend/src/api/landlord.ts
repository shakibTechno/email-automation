import apiClient from './client';
import type {
  DeliverabilityResponse,
  PlatformOverview,
  RevenueSummary,
  TenantDetail,
  TenantListParams,
  TenantListResponse,
} from '@/types/landlord';

const BASE_URL = '/landlord';

export async function getOverview(days = 30, refresh = false): Promise<PlatformOverview> {
  const { data } = await apiClient.get<PlatformOverview>(`${BASE_URL}/overview`, {
    params: { days, ...(refresh ? { refresh: 1 } : {}) },
  });
  return data;
}

export async function getDeliverability(): Promise<DeliverabilityResponse> {
  const { data } = await apiClient.get<DeliverabilityResponse>(`${BASE_URL}/deliverability`);
  return data;
}

export async function getRevenue(): Promise<RevenueSummary> {
  const { data } = await apiClient.get<RevenueSummary>(`${BASE_URL}/revenue`);
  return data;
}

export async function getTenants(params?: TenantListParams): Promise<TenantListResponse> {
  const { data } = await apiClient.get<TenantListResponse>(`${BASE_URL}/tenants`, { params });
  return data;
}

export async function getTenant(id: string): Promise<TenantDetail> {
  const { data } = await apiClient.get<TenantDetail>(`${BASE_URL}/tenants/${id}`);
  return data;
}

export async function suspendSending(id: string, reason: string): Promise<TenantDetail> {
  const { data } = await apiClient.post<TenantDetail>(
    `${BASE_URL}/tenants/${id}/suspend-sending`, { reason },
  );
  return data;
}

export async function resumeSending(id: string): Promise<TenantDetail> {
  const { data } = await apiClient.post<TenantDetail>(
    `${BASE_URL}/tenants/${id}/resume-sending`, {},
  );
  return data;
}

export async function suspendAccount(id: string, reason: string): Promise<TenantDetail> {
  const { data } = await apiClient.post<TenantDetail>(
    `${BASE_URL}/tenants/${id}/suspend-account`, { reason },
  );
  return data;
}

export async function restoreAccount(id: string, resumeSending = true): Promise<TenantDetail> {
  const { data } = await apiClient.post<TenantDetail>(
    `${BASE_URL}/tenants/${id}/restore-account`, { resume_sending: resumeSending },
  );
  return data;
}
