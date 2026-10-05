import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Loader2 } from 'lucide-react';
import type { AnalyticsIntegration, AnalyticsProvider, UpsertAnalyticsData } from '@/types/integration';

interface AnalyticsProviderCardProps {
  integration?: AnalyticsIntegration;
  provider: AnalyticsProvider;
  onSave: (data: UpsertAnalyticsData) => void;
  onRemove: (provider: AnalyticsProvider) => void;
  isSaving: boolean;
}

const PROVIDER_CONFIG: Record<AnalyticsProvider, {
  name: string;
  abbreviation: string;
  color: string;
  description: string;
  placeholder: string;
}> = {
  google_analytics: {
    name: 'Google Analytics',
    abbreviation: 'GA',
    color: 'bg-orange-500',
    description: 'Track website traffic, user behavior, and conversions with Google Analytics.',
    placeholder: 'UA-XXXXXXXXX-X or G-XXXXXXXXXX',
  },
  facebook_pixel: {
    name: 'Facebook Pixel',
    abbreviation: 'FP',
    color: 'bg-blue-600',
    description: 'Track conversions from Facebook ads, optimize ads, and build targeted audiences.',
    placeholder: 'XXXXXXXXXXXXXXXX',
  },
  google_tag_manager: {
    name: 'Google Tag Manager',
    abbreviation: 'GTM',
    color: 'bg-sky-500',
    description: 'Manage and deploy marketing tags on your website without modifying code.',
    placeholder: 'GTM-XXXXXXX',
  },
};

export function AnalyticsProviderCard({
  integration,
  provider,
  onSave,
  onRemove,
  isSaving,
}: AnalyticsProviderCardProps) {
  const config = PROVIDER_CONFIG[provider];
  const [trackingId, setTrackingId] = useState(integration?.tracking_id || '');
  const [isEnabled, setIsEnabled] = useState(integration?.is_enabled ?? true);

  useEffect(() => {
    setTrackingId(integration?.tracking_id || '');
    setIsEnabled(integration?.is_enabled ?? true);
  }, [integration]);

  const handleSave = () => {
    if (!trackingId.trim()) return;
    onSave({
      provider,
      tracking_id: trackingId.trim(),
      is_enabled: isEnabled,
    });
  };

  const handleRemove = () => {
    onRemove(provider);
  };

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
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor={`tracking-id-${provider}`}>Tracking ID</Label>
          <Input
            id={`tracking-id-${provider}`}
            value={trackingId}
            onChange={(e) => setTrackingId(e.target.value)}
            placeholder={config.placeholder}
          />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor={`enabled-${provider}`} className="text-sm">
            Enable tracking
          </Label>
          <Switch
            id={`enabled-${provider}`}
            checked={isEnabled}
            onCheckedChange={setIsEnabled}
          />
        </div>

        <div className="flex items-center gap-2 pt-2">
          <Button
            onClick={handleSave}
            disabled={isSaving || !trackingId.trim()}
            className="flex-1"
          >
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Saving...
              </>
            ) : (
              'Save'
            )}
          </Button>
          {integration && (
            <Button
              variant="outline"
              onClick={handleRemove}
              disabled={isSaving}
              className="text-destructive hover:text-destructive"
            >
              Remove
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
