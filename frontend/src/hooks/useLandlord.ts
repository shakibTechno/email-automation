import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as landlordApi from '@/api/landlord';
import type { TenantListParams } from '@/types/landlord';

// Shorter than analytics' five minutes: an operator looking at this is usually
// acting on it, and a suspension that does not appear to have taken effect is
// worse than a slightly chattier console.
const STALE_TIME = 1000 * 60;

export const landlordKeys = {
  all: ['landlord'] as const,
  overview: (days: number) => [...landlordKeys.all, 'overview', days] as const,
  deliverability: () => [...landlordKeys.all, 'deliverability'] as const,
  revenue: () => [...landlordKeys.all, 'revenue'] as const,
  tenants: (params?: TenantListParams) => [...landlordKeys.all, 'tenants', params] as const,
  tenant: (id: string) => [...landlordKeys.all, 'tenant', id] as const,
};

export function usePlatformOverview(days = 30) {
  return useQuery({
    queryKey: landlordKeys.overview(days),
    queryFn: () => landlordApi.getOverview(days),
    staleTime: STALE_TIME,
  });
}

export function useDeliverability() {
  return useQuery({
    queryKey: landlordKeys.deliverability(),
    queryFn: landlordApi.getDeliverability,
    staleTime: STALE_TIME,
  });
}

export function useRevenue() {
  return useQuery({
    queryKey: landlordKeys.revenue(),
    queryFn: landlordApi.getRevenue,
    staleTime: STALE_TIME,
  });
}

export function useTenants(params?: TenantListParams) {
  const { data, isLoading, error } = useQuery({
    queryKey: landlordKeys.tenants(params),
    queryFn: () => landlordApi.getTenants(params),
    staleTime: STALE_TIME,
  });

  return {
    tenants: data?.results ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? 1,
    perPage: data?.per_page ?? 25,
    totalPages: data?.total_pages ?? 0,
    isLoading,
    error,
  };
}

export function useTenant(id?: string) {
  return useQuery({
    queryKey: landlordKeys.tenant(id ?? ''),
    queryFn: () => landlordApi.getTenant(id as string),
    enabled: !!id,
    staleTime: STALE_TIME,
  });
}

/**
 * Suspension actions. Each invalidates the whole landlord tree rather than one
 * key: suspending a tenant changes the tenant row, the risk board and the
 * overview counts at once, and a console showing one of them stale is how an
 * operator ends up suspending something twice.
 */
export function useTenantActions(id: string) {
  const queryClient = useQueryClient();

  const invalidate = () => queryClient.invalidateQueries({ queryKey: landlordKeys.all });

  const onError = (error: { message?: string }, fallback: string) =>
    toast.error(error?.message || fallback);

  const suspendSending = useMutation({
    mutationFn: (reason: string) => landlordApi.suspendSending(id, reason),
    onSuccess: () => { invalidate(); toast.success('Sending suspended.'); },
    onError: (e: { message?: string }) => onError(e, 'Could not suspend sending'),
  });

  const resumeSending = useMutation({
    mutationFn: () => landlordApi.resumeSending(id),
    onSuccess: () => { invalidate(); toast.success('Sending resumed.'); },
    onError: (e: { message?: string }) => onError(e, 'Could not resume sending'),
  });

  const suspendAccount = useMutation({
    mutationFn: (reason: string) => landlordApi.suspendAccount(id, reason),
    onSuccess: () => { invalidate(); toast.success('Account suspended.'); },
    onError: (e: { message?: string }) => onError(e, 'Could not suspend the account'),
  });

  const restoreAccount = useMutation({
    mutationFn: (resume: boolean) => landlordApi.restoreAccount(id, resume),
    onSuccess: () => { invalidate(); toast.success('Account restored.'); },
    onError: (e: { message?: string }) => onError(e, 'Could not restore the account'),
  });

  return {
    suspendSending,
    resumeSending,
    suspendAccount,
    restoreAccount,
    isBusy:
      suspendSending.isPending ||
      resumeSending.isPending ||
      suspendAccount.isPending ||
      restoreAccount.isPending,
  };
}
