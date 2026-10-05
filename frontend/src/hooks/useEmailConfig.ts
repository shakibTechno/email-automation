import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emailConfigApi } from '@/api/emailConfig';
import type { UpdateEmailConfigData } from '@/types/emailConfig';

const QK = 'email-config';
const QK_DOMAINS = 'email-config-domains';

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

export function useEmailConfigMutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: [QK] });
  };
  const invalidateDomains = () => {
    qc.invalidateQueries({ queryKey: [QK_DOMAINS] });
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

  return { updateConfig, testConnection, resumeSending, addDomain, verifyDomain, deleteDomain };
}
