import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Loader2, RefreshCw, Unplug, Info, Users, Clock, User,
  ChevronDown, ChevronUp, Eye, EyeOff, Key, Save,
} from 'lucide-react';
import { FieldMappingEditor } from './FieldMappingEditor';
import { SyncHistoryTable } from './SyncHistoryTable';
import type {
  SocialIntegration,
  SocialPlatform,
  UpdateSocialData,
  UpdateCredentialsData,
  LeadSyncLog,
  FieldMappingOption,
} from '@/types/integration';

interface SocialPlatformCardProps {
  integration: SocialIntegration;
  onConnect: () => void;
  onDisconnect: () => void;
  onSync: () => void;
  onUpdateSettings: (data: UpdateSocialData) => void;
  onSaveCredentials: (data: UpdateCredentialsData) => void;
  onRealConnect: () => void;
  syncHistory: LeadSyncLog[];
  fieldMappingOptions: FieldMappingOption[];
  isConnecting: boolean;
  isSyncing: boolean;
  isSavingCredentials: boolean;
  isRealConnecting: boolean;
}

const PLATFORM_CONFIG: Record<SocialPlatform, {
  name: string;
  abbreviation: string;
  color: string;
  description: string;
  credentialsHelp: string;
}> = {
  facebook_lead_ads: {
    name: 'Facebook Lead Ads',
    abbreviation: 'FB',
    color: 'bg-primary',
    description: 'Automatically import leads from your Facebook Lead Ad campaigns into your contact list.',
    credentialsHelp: 'Find your App ID and App Secret in the Facebook Developers portal under your app settings. The Page ID is found in your Facebook Page\'s About section.',
  },
  linkedin_lead_gen: {
    name: 'LinkedIn Lead Gen Forms',
    abbreviation: 'LI',
    color: 'bg-primary',
    description: 'Sync leads from LinkedIn Lead Gen Form campaigns directly into your contact list.',
    credentialsHelp: 'Find your App ID (Client ID) and App Secret (Client Secret) in the LinkedIn Developers portal. The Organization ID is in your LinkedIn Company Page admin URL.',
  },
};

const SYNC_INTERVAL_OPTIONS = [
  { value: '15', label: 'Every 15 minutes' },
  { value: '30', label: 'Every 30 minutes' },
  { value: '60', label: 'Every 1 hour' },
  { value: '120', label: 'Every 2 hours' },
  { value: '240', label: 'Every 4 hours' },
  { value: '720', label: 'Every 12 hours' },
  { value: '1440', label: 'Every 24 hours' },
];

function CredentialsForm({
  integration,
  onSave,
  isSaving,
}: {
  integration: SocialIntegration;
  onSave: (data: UpdateCredentialsData) => void;
  isSaving: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [appId, setAppId] = useState(integration.credentials_display?.app_id || '');
  const [appSecret, setAppSecret] = useState('');
  const [pageId, setPageId] = useState(integration.credentials_display?.page_id || '');
  const [orgId, setOrgId] = useState(integration.credentials_display?.organization_id || '');

  const config = PLATFORM_CONFIG[integration.platform];
  const isFacebook = integration.platform === 'facebook_lead_ads';

  useEffect(() => {
    setAppId(integration.credentials_display?.app_id || '');
    setPageId(integration.credentials_display?.page_id || '');
    setOrgId(integration.credentials_display?.organization_id || '');
    // Don't reset appSecret - it's masked from server
  }, [integration.credentials_display]);

  const handleSave = () => {
    if (!appId.trim() || !appSecret.trim()) return;
    onSave({
      app_id: appId.trim(),
      app_secret: appSecret.trim(),
      ...(isFacebook ? { page_id: pageId.trim() } : { organization_id: orgId.trim() }),
    });
    setAppSecret('');
  };

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm font-semibold hover:text-foreground/80 transition-colors w-full"
      >
        <Key className="h-4 w-4" />
        API Configuration
        {integration.has_credentials && (
          <Badge variant="outline" className="ml-1 text-xs bg-success/[.10] text-success border-success/[.30]">
            Configured
          </Badge>
        )}
        {expanded ? (
          <ChevronUp className="h-4 w-4 ml-auto" />
        ) : (
          <ChevronDown className="h-4 w-4 ml-auto" />
        )}
      </button>

      {expanded && (
        <div className="space-y-4 pl-6 pt-1">
          <p className="text-xs text-muted-foreground">
            {config.credentialsHelp}
          </p>

          <div className="grid gap-3">
            <div className="space-y-1.5">
              <Label htmlFor={`app-id-${integration.id}`} className="text-sm">
                App ID
              </Label>
              <Input
                id={`app-id-${integration.id}`}
                value={appId}
                onChange={(e) => setAppId(e.target.value)}
                placeholder="Enter your App ID"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor={`app-secret-${integration.id}`} className="text-sm">
                App Secret
              </Label>
              <div className="relative">
                <Input
                  id={`app-secret-${integration.id}`}
                  type={showSecret ? 'text' : 'password'}
                  value={appSecret}
                  onChange={(e) => setAppSecret(e.target.value)}
                  placeholder={
                    integration.has_credentials
                      ? `Current: ${integration.credentials_display?.app_secret || '••••'} (enter new to update)`
                      : 'Enter your App Secret'
                  }
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowSecret(!showSecret)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {isFacebook ? (
              <div className="space-y-1.5">
                <Label htmlFor={`page-id-${integration.id}`} className="text-sm">
                  Page ID <span className="text-muted-foreground font-normal">(optional)</span>
                </Label>
                <Input
                  id={`page-id-${integration.id}`}
                  value={pageId}
                  onChange={(e) => setPageId(e.target.value)}
                  placeholder="Enter your Facebook Page ID"
                />
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label htmlFor={`org-id-${integration.id}`} className="text-sm">
                  Organization ID <span className="text-muted-foreground font-normal">(optional)</span>
                </Label>
                <Input
                  id={`org-id-${integration.id}`}
                  value={orgId}
                  onChange={(e) => setOrgId(e.target.value)}
                  placeholder="Enter your LinkedIn Organization ID"
                />
              </div>
            )}
          </div>

          <Button
            size="sm"
            onClick={handleSave}
            disabled={isSaving || !appId.trim() || !appSecret.trim()}
          >
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Credentials
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

export function SocialPlatformCard({
  integration,
  onConnect,
  onDisconnect,
  onSync,
  onUpdateSettings,
  onSaveCredentials,
  onRealConnect,
  syncHistory,
  fieldMappingOptions,
  isConnecting,
  isSyncing,
  isSavingCredentials,
  isRealConnecting,
}: SocialPlatformCardProps) {
  const config = PLATFORM_CONFIG[integration.platform];
  const isConnected = integration.status === 'connected';

  const [autoSync, setAutoSync] = useState(integration.auto_sync);
  const [syncInterval, setSyncInterval] = useState(String(integration.sync_interval_minutes));
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>(integration.field_mapping);

  useEffect(() => {
    setAutoSync(integration.auto_sync);
    setSyncInterval(String(integration.sync_interval_minutes));
    setFieldMapping(integration.field_mapping);
  }, [integration]);

  const handleSaveSettings = () => {
    onUpdateSettings({
      auto_sync: autoSync,
      sync_interval_minutes: parseInt(syncInterval, 10),
      field_mapping: fieldMapping,
    });
  };

  // Disconnected state
  if (!isConnected) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className={`${config.color} text-white font-bold text-sm rounded-lg w-10 h-10 flex items-center justify-center`}>
              {config.abbreviation}
            </div>
            <div className="flex-1">
              <CardTitle className="text-base">{config.name}</CardTitle>
              <CardDescription className="text-xs">{config.description}</CardDescription>
            </div>
            <Badge variant="secondary">Disconnected</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <CredentialsForm
            integration={integration}
            onSave={onSaveCredentials}
            isSaving={isSavingCredentials}
          />

          <div className="flex items-center gap-2">
            {integration.has_credentials && (
              <Button onClick={onRealConnect} disabled={isRealConnecting}>
                {isRealConnecting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Connecting...
                  </>
                ) : (
                  'Connect'
                )}
              </Button>
            )}
            <Button variant="outline" onClick={onConnect} disabled={isConnecting}>
              {isConnecting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Connecting...
                </>
              ) : (
                'Connect (Demo)'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Connected state
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className={`${config.color} text-white font-bold text-sm rounded-lg w-10 h-10 flex items-center justify-center`}>
            {config.abbreviation}
          </div>
          <div className="flex-1">
            <CardTitle className="text-base">{config.name}</CardTitle>
            <CardDescription className="text-xs">{config.description}</CardDescription>
          </div>
          <Badge className="bg-success/[.14] text-success hover:bg-success/[.14]">
            Connected{integration.is_demo ? ' (Demo)' : ''}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Account Info */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="flex items-center gap-2 text-sm">
            <User className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-muted-foreground text-xs">Account</p>
              <p className="font-medium">{integration.external_account_name || '-'}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Users className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-muted-foreground text-xs">Total Leads Imported</p>
              <p className="font-medium">{integration.total_leads_imported.toLocaleString()}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-muted-foreground text-xs">Connected By</p>
              <p className="font-medium">{integration.connected_by_name || '-'}</p>
            </div>
          </div>
        </div>

        {/* Demo Mode Alert */}
        {integration.is_demo && (
          <div className="flex items-start gap-3 rounded-lg border p-4 bg-muted/50">
            <Info className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
            <p className="text-sm text-muted-foreground">
              Running in demo mode. Enter your API credentials and reconnect for live data.
            </p>
          </div>
        )}

        <div className="border-t" />

        {/* API Configuration (collapsible) */}
        <CredentialsForm
          integration={integration}
          onSave={onSaveCredentials}
          isSaving={isSavingCredentials}
        />

        <div className="border-t" />

        {/* Sync Settings */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold">Sync Settings</h4>
          <div className="flex items-center justify-between">
            <Label htmlFor={`auto-sync-${integration.id}`} className="text-sm">
              Auto-sync leads
            </Label>
            <Switch
              id={`auto-sync-${integration.id}`}
              checked={autoSync}
              onCheckedChange={setAutoSync}
            />
          </div>
          {autoSync && (
            <div className="space-y-2">
              <Label htmlFor={`sync-interval-${integration.id}`} className="text-sm">
                Sync interval
              </Label>
              <Select value={syncInterval} onValueChange={setSyncInterval}>
                <SelectTrigger id={`sync-interval-${integration.id}`} className="w-full sm:w-64">
                  <SelectValue placeholder="Select interval" />
                </SelectTrigger>
                <SelectContent>
                  {SYNC_INTERVAL_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <div className="border-t" />

        {/* Field Mapping */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold">Field Mapping</h4>
          <p className="text-xs text-muted-foreground">
            Map platform lead fields to your contact fields.
          </p>
          <FieldMappingEditor
            mapping={fieldMapping}
            onChange={setFieldMapping}
            options={fieldMappingOptions}
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          <Button onClick={handleSaveSettings}>
            Save Settings
          </Button>
          <Button
            variant="outline"
            onClick={onSync}
            disabled={isSyncing}
          >
            {isSyncing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Syncing...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Sync Now
              </>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={onDisconnect}
            className="text-destructive hover:text-destructive"
          >
            <Unplug className="h-4 w-4 mr-2" />
            Disconnect
          </Button>
        </div>

        <div className="border-t" />

        {/* Sync History */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold">Sync History</h4>
          <SyncHistoryTable logs={syncHistory} />
        </div>
      </CardContent>
    </Card>
  );
}
