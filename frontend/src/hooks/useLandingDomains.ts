import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as api from '@/api/landingDomains';
import type { LandingDomain } from '@/types/landing-page';

export const landingDomainKeys = {
  all: ['landing-domains'] as const,
  list: () => [...landingDomainKeys.all, 'list'] as const,
};

export function useLandingDomains(enabled = true) {
  const { data, isLoading, error } = useQuery({
    queryKey: landingDomainKeys.list(),
    queryFn: api.listDomains,
    enabled,
    staleTime: 1000 * 30,
  });

  return { domains: data ?? [], isLoading, error };
}

export function useLandingDomainActions() {
  const queryClient = useQueryClient();

  // Landing page queries are invalidated too: a domain verifying changes every
  // page's public_url, and a stale copy would have the customer copying a link
  // to the wrong host.
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: landingDomainKeys.all });
    queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
  };

  const onError = (error: { message?: string }, fallback: string) =>
    toast.error(error?.message || fallback);

  const connect = useMutation({
    mutationFn: (domain: string) => api.connectDomain(domain),
    onSuccess: () => {
      invalidate();
      toast.success('Domain added. Publish the DNS record to bring it live.');
    },
    onError: (e: { message?: string }) => onError(e, 'Could not add that domain'),
  });

  const verify = useMutation({
    mutationFn: (id: string) => api.verifyDomain(id),
    onSuccess: (domain: LandingDomain) => {
      invalidate();
      // Not a failure toast: the request succeeded, the domain just is not
      // ready. Saying "error" here sends people looking for the wrong problem.
      if (domain.is_verified) {
        toast.success(`${domain.domain} is live.`);
      } else {
        toast.info(domain.last_check_error || 'Not ready yet.');
      }
    },
    onError: (e: { message?: string }) => onError(e, 'Could not check that domain'),
  });

  const setPrimary = useMutation({
    mutationFn: (id: string) => api.setPrimaryDomain(id),
    onSuccess: () => {
      invalidate();
      toast.success('Default domain updated.');
    },
    onError: (e: { message?: string }) => onError(e, 'Could not set the default domain'),
  });

  const disconnect = useMutation({
    mutationFn: (id: string) => api.disconnectDomain(id),
    onSuccess: () => {
      invalidate();
      toast.success('Domain removed.');
    },
    onError: (e: { message?: string }) => onError(e, 'Could not remove that domain'),
  });

  return {
    connect,
    verify,
    setPrimary,
    disconnect,
    isBusy:
      connect.isPending ||
      verify.isPending ||
      setPrimary.isPending ||
      disconnect.isPending,
  };
}
