import { FlaskConical, X } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ABTestConfig, ABTestType } from '@/types/campaign';

interface ABTestConfigPanelProps {
  config: ABTestConfig;
  onChange: (config: ABTestConfig) => void;
  onRemove: () => void;
  campaignSubject: string;
  campaignSenderName: string;
  templates: { id: string; name: string }[];
}

export const ABTestConfigPanel = ({
  config,
  onChange,
  onRemove,
  campaignSubject,
  campaignSenderName,
  templates,
}: ABTestConfigPanelProps) => {
  const set = <K extends keyof ABTestConfig>(key: K, value: ABTestConfig[K]) =>
    onChange({ ...config, [key]: value });

  return (
    <Card className="p-5 space-y-4 border-primary/30 bg-primary/5">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2 text-primary">
          <FlaskConical className="h-4 w-4" /> A/B Test Configuration
        </h3>
        <Button variant="ghost" size="sm" onClick={onRemove} className="h-7 w-7 p-0">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Test type */}
        <div className="space-y-2">
          <Label>What to test</Label>
          <Select
            value={config.test_type}
            onValueChange={(v) => set('test_type', v as ABTestType)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="subject">Subject Line</SelectItem>
              <SelectItem value="sender_name">Sender Name</SelectItem>
              <SelectItem value="content">Email Content (Template)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Test percentage */}
        <div className="space-y-2">
          <Label>Test audience split (%)</Label>
          <Input
            type="number"
            min={10}
            max={50}
            value={config.test_percentage}
            onChange={(e) => set('test_percentage', Number(e.target.value))}
          />
          <p className="text-xs text-muted-foreground">
            {config.test_percentage / 2}% → A, {config.test_percentage / 2}% → B,{' '}
            {100 - config.test_percentage}% → winner group
          </p>
        </div>

        {/* Winner criteria */}
        <div className="space-y-2">
          <Label>Winner criteria</Label>
          <Select
            value={config.winner_criteria}
            onValueChange={(v) => set('winner_criteria', v as ABTestConfig['winner_criteria'])}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="open_rate">Open Rate</SelectItem>
              <SelectItem value="click_rate">Click Rate</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Winner selection */}
        <div className="space-y-2">
          <Label>Winner selection</Label>
          <Select
            value={config.winner_selection}
            onValueChange={(v) => set('winner_selection', v as ABTestConfig['winner_selection'])}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Automatic (after duration)</SelectItem>
              <SelectItem value="manual">Manual (I'll decide)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Duration — only relevant for auto */}
        {config.winner_selection === 'auto' && (
          <div className="space-y-2">
            <Label>Test duration (hours)</Label>
            <Input
              type="number"
              min={1}
              max={168}
              value={config.test_duration_hours}
              onChange={(e) => set('test_duration_hours', Number(e.target.value))}
            />
          </div>
        )}
      </div>

      {/* Variant B value */}
      <div className="border-t pt-4 space-y-3">
        <p className="text-sm font-medium">Variant B (Challenger)</p>
        <p className="text-xs text-muted-foreground">
          Variant A is automatically your campaign's current settings.
        </p>

        {config.test_type === 'subject' && (
          <div className="space-y-2">
            <Label>Variant B subject line *</Label>
            <Input
              placeholder={campaignSubject || 'Enter alternative subject…'}
              value={config.variant_b_subject ?? ''}
              onChange={(e) => set('variant_b_subject', e.target.value)}
            />
          </div>
        )}

        {config.test_type === 'sender_name' && (
          <div className="space-y-2">
            <Label>Variant B sender name *</Label>
            <Input
              placeholder={campaignSenderName || 'Enter alternative sender name…'}
              value={config.variant_b_sender_name ?? ''}
              onChange={(e) => set('variant_b_sender_name', e.target.value)}
            />
          </div>
        )}

        {config.test_type === 'content' && (
          <div className="space-y-2">
            <Label>Variant B template *</Label>
            <Select
              value={config.variant_b_template ?? ''}
              onValueChange={(v) => set('variant_b_template', v || null)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a template…" />
              </SelectTrigger>
              <SelectContent>
                {templates.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>
    </Card>
  );
};
