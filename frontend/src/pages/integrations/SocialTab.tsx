import { Loader2 } from 'lucide-react';
import {
  useSocialIntegrations,
  useIntegrationMutations,
  useFieldMappingOptions,
  useSyncHistory,
} from '@/hooks/useIntegrations';
import { SocialPlatformCard } from '@/components/integrations/SocialPlatformCard';
import type { SocialIntegration, SocialPlatform } from '@/types/integration';

const PLATFORMS: SocialPlatform[] = ['facebook_lead_ads', 'linkedin_lead_gen'];

function SocialPlatformCardWrapper({ integration }: { integration: SocialIntegration }) {
  const { demoConnect, disconnect, updateSocial, updateCredentials, connect, syncLeads } = useIntegrationMutations();
  const { data: fieldMappingOptions } = useFieldMappingOptions();
  const isConnected = integration.status === 'connected';
  const { data: syncHistory } = useSyncHistory(integration.id, isConnected);

  return (
    <SocialPlatformCard
      integration={integration}
      onConnect={() => demoConnect.mutate({ platform: integration.platform })}
      onDisconnect={() => disconnect.mutate(integration.id)}
      onSync={() => syncLeads.mutate(integration.id)}
      onUpdateSettings={(data) => updateSocial.mutate({ id: integration.id, data })}
      onSaveCredentials={(data) => updateCredentials.mutate({ id: integration.id, data })}
      onRealConnect={() => connect.mutate(integration.id)}
      syncHistory={syncHistory || []}
      fieldMappingOptions={fieldMappingOptions || []}
      isConnecting={demoConnect.isPending}
      isSyncing={syncLeads.isPending}
      isSavingCredentials={updateCredentials.isPending}
      isRealConnecting={connect.isPending}
    />
  );
}

export function SocialTab() {
  const { data: integrations, isLoading } = useSocialIntegrations();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Build a list of all platforms, using existing integration data or a disconnected stub
  const platformCards = PLATFORMS.map((platform) => {
    const existing = integrations?.find((i) => i.platform === platform);
    if (existing) {
      return existing;
    }
    // Create a disconnected stub for platforms without an integration record
    return {
      id: `stub-${platform}`,
      platform,
      status: 'disconnected' as const,
      external_account_id: '',
      external_account_name: '',
      auto_sync: false,
      sync_interval_minutes: 60,
      last_synced_at: null,
      field_mapping: {},
      default_tag: null,
      default_tag_name: null,
      total_leads_imported: 0,
      is_demo: false,
      has_credentials: false,
      credentials_display: {},
      connected_by_name: null,
      created_at: '',
      updated_at: '',
    };
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Social Media Integrations</h2>
        <p className="text-sm text-muted-foreground">
          Connect your social media advertising platforms to automatically import leads into your contact list.
        </p>
      </div>

      <div className="space-y-6">
        {platformCards.map((integration) => (
          <SocialPlatformCardWrapper key={integration.platform} integration={integration} />
        ))}
      </div>
    </div>
  );
}
