import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emailConfigApi } from '@/api/emailConfig';
import type { UpdateEmailConfigData } from '@/types/emailConfig';

const QK = 'email-config';
const QK_DOMAINS = 'email-config-domains';
const QK_TENANT = 'email-config-tenant';

export function useEmailConfig() {
  return useQuery({
    queryKey: [QK],
    queryFn: emailConfigApi.getConfig,
    staleTime: 30000,
  });
}

export function useSendingDomains() {
  return useQuery({
    queryKey: [QK_DOMAINS],
    queryFn: emailConfigApi.getDomains,
  });
}

/** The organization's mail server. Resolves to null until a domain is added. */
export function usePostalTenant() {
  return useQuery({
    queryKey: [QK_TENANT],
    queryFn: emailConfigApi.getTenant,
    staleTime: 30000,
  });
}

export function useEmailConfigMutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: [QK] });
  };
  const invalidateDomains = () => {
    qc.invalidateQueries({ queryKey: [QK_DOMAINS] });
    // Adding the first domain is what provisions the mail server, and
    // verifying one changes whether it can send, so the tenant panel is stale
    // after either.
    qc.invalidateQueries({ queryKey: [QK_TENANT] });
  };

  const updateConfig = useMutation({
    mutationFn: (data: UpdateEmailConfigData) => emailConfigApi.updateConfig(data),
    onSuccess: () => invalidate(),
  });

  const testConnection = useMutation({
    mutationFn: (toEmail: string) => emailConfigApi.testConnection(toEmail),
  });

  const resumeSending = useMutation({
    mutationFn: () => emailConfigApi.resumeSending(),
    onSuccess: () => invalidate(),
  });

  const addDomain = useMutation({
    mutationFn: (domain: string) => emailConfigApi.addDomain(domain),
    onSuccess: () => invalidateDomains(),
  });

  const verifyDomain = useMutation({
    mutationFn: (id: string) => emailConfigApi.verifyDomain(id),
    onSuccess: () => invalidateDomains(),
  });

  const deleteDomain = useMutation({
    mutationFn: (id: string) => emailConfigApi.deleteDomain(id),
    onSuccess: () => invalidateDomains(),
  });

  const syncTenant = useMutation({
    mutationFn: () => emailConfigApi.syncTenant(),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK_TENANT] }),
  });

  return {
    updateConfig,
    testConnection,
    resumeSending,
    addDomain,
    verifyDomain,
    deleteDomain,
    syncTenant,
  };
}
