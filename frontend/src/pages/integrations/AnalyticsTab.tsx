import { Loader2 } from 'lucide-react';
import { useAnalyticsIntegrations, useIntegrationMutations } from '@/hooks/useIntegrations';
import { AnalyticsProviderCard } from '@/components/integrations/AnalyticsProviderCard';
import type { AnalyticsProvider } from '@/types/integration';

const PROVIDERS: AnalyticsProvider[] = ['google_analytics', 'facebook_pixel', 'google_tag_manager'];

export function AnalyticsTab() {
  const { data: integrations, isLoading } = useAnalyticsIntegrations();
  const { upsertAnalytics, deleteAnalytics } = useIntegrationMutations();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Analytics Integrations</h2>
        <p className="text-sm text-muted-foreground">
          Connect your analytics platforms to track visitor activity across your landing pages and forms.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {PROVIDERS.map((provider) => {
          const existing = integrations?.find((i) => i.provider === provider);
          return (
            <AnalyticsProviderCard
              key={provider}
              provider={provider}
              integration={existing}
              onSave={(data) => upsertAnalytics.mutate(data)}
              onRemove={(p) => deleteAnalytics.mutate(p)}
              isSaving={upsertAnalytics.isPending || deleteAnalytics.isPending}
            />
          );
        })}
      </div>
    </div>
  );
}
