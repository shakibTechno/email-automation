import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
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
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { AlertTriangle, CheckCircle2, KeyRound, Loader2, Sparkles } from 'lucide-react';
import { useAIConfig, useTestAIConnection, useUpdateAIConfig } from '@/hooks/useAI';
import { usePermissions } from '@/hooks/usePermissions';
import { aiProviderLabels } from '@/types/ai';
import type { AIProvider } from '@/types/ai';

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
        {description && <CardDescription className="text-sm">{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

const KEY_HELP: Record<AIProvider, string> = {
  anthropic: 'Create one at console.anthropic.com → API Keys.',
  openai: 'Create one at platform.openai.com → API keys.',
  google: 'Create one at aistudio.google.com → Get API key.',
  local: 'Most self-hosted servers need no key — leave this blank unless yours does.',
};

export function AITab() {
  const { config, isLoading } = useAIConfig();
  const updateConfig = useUpdateAIConfig();
  const testConnection = useTestAIConnection();
  const { canManageTeam } = usePermissions();

  const [provider, setProvider] = useState<AIProvider>('anthropic');
  const [model, setModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [isEnabled, setIsEnabled] = useState(false);

  useEffect(() => {
    if (!config) return;
    setProvider(config.provider);
    setModel(config.model);
    setBaseUrl(config.base_url);
    setIsEnabled(config.is_enabled);
    // Never seeded from the server — the key is write-only, and an empty
    // field means "leave the stored one alone".
    setApiKey('');
  }, [config]);

  if (isLoading || !config) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-5 w-5 animate-spin text-subtle-foreground" />
      </div>
    );
  }

  // A self-hosted server is identified by where it is, not by a credential.
  const isSelfHosted = provider === 'local';
  const hasConnection = isSelfHosted ? Boolean(baseUrl.trim()) : config.api_key_set;

  const handleSave = () => {
    updateConfig.mutate(
      {
        provider,
        model: model.trim(),
        base_url: baseUrl.trim(),
        is_enabled: isEnabled,
        ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
      },
      { onSuccess: () => setApiKey('') }
    );
  };

  return (
    <div className="space-y-4">
      <SectionCard
        title="AI provider"
        description="Connect your own account to generate landing pages from a description. Generation runs on your key, billed by your provider."
      >
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="ai-provider">Provider</Label>
              <Select
                value={provider}
                onValueChange={(v) => setProvider(v as AIProvider)}
                disabled={!canManageTeam}
              >
                <SelectTrigger id="ai-provider">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(aiProviderLabels) as AIProvider[]).map((key) => (
                    <SelectItem key={key} value={key}>
                      {aiProviderLabels[key]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="ai-model">
                Model <span className="text-subtle-foreground">(optional)</span>
              </Label>
              {/* Chrome reads any text input sitting above a password field
                  as the username half of a login form and fills it with the
                  saved account email. A name that is not credential-shaped,
                  plus autoComplete off, keeps it out of that heuristic. */}
              <Input
                id="ai-model"
                name="llm-model-identifier"
                autoComplete="off"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder={config.effective_model || 'Provider default'}
                disabled={!canManageTeam}
              />
              <p className="text-xs text-muted-foreground">
                {isSelfHosted
                  ? 'Leave blank to use whichever model the server has loaded.'
                  : `Leave blank to use ${config.effective_model || 'the provider default'}.`}
              </p>
            </div>
          </div>

          {isSelfHosted && (
            <div className="space-y-1.5">
              <Label htmlFor="ai-base-url">Server address</Label>
              <Input
                id="ai-base-url"
                name="llm-server-address"
                autoComplete="off"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="http://192.168.1.10:8080"
                disabled={!canManageTeam}
              />
              <p className="text-xs text-muted-foreground">
                The root address of your llama.cpp or Ollama server — the part before
                <code className="mx-1 rounded bg-secondary px-1 py-0.5 text-[11px]">/v1</code>.
                It must be reachable from the server this app runs on, not just from your
                own machine.
              </p>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="ai-key">
              API key
              {isSelfHosted && (
                <span className="text-subtle-foreground"> (usually not needed)</span>
              )}
            </Label>
            {/* `autoComplete="off"` is ignored on password inputs — Chrome
                filled this with the user's account password, which they would
                then have saved as an LLM key. "new-password" is the value
                browsers actually honour for a secret that is being set rather
                than recalled. */}
            <Input
              id="ai-key"
              name="llm-provider-secret"
              type="password"
              autoComplete="new-password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={config.api_key_set ? '•••••••• (saved)' : 'Paste your API key'}
              disabled={!canManageTeam}
            />
            <p className="text-xs text-muted-foreground">
              {KEY_HELP[provider]}{' '}
              {config.api_key_set
                ? 'A key is saved. Leave this blank to keep it, or paste a new one to replace it.'
                : 'The key is stored on your organization and never shown again once saved.'}
            </p>
          </div>

          <div className="flex items-center justify-between rounded-md border p-3">
            <div>
              <p className="text-[13px] font-medium">Enable AI page generation</p>
              <p className="text-xs text-muted-foreground">
                Adds a “Generate with AI” option when creating a landing page.
              </p>
            </div>
            <Switch
              checked={isEnabled}
              onCheckedChange={setIsEnabled}
              disabled={!canManageTeam || !hasConnection}
            />
          </div>

          {!hasConnection && (
            <p className="flex items-start gap-2 text-[12.5px] text-muted-foreground">
              <KeyRound className="mt-0.5 h-3.5 w-3.5 flex-none" />
              {isSelfHosted
                ? 'Enter the server address first — generation cannot be enabled without one.'
                : 'Save a key first — generation cannot be enabled without one.'}
            </p>
          )}

          {canManageTeam && (
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={handleSave} disabled={updateConfig.isPending}>
                {updateConfig.isPending ? 'Saving…' : 'Save settings'}
              </Button>
              <Button
                variant="outline"
                onClick={() => testConnection.mutate()}
                disabled={testConnection.isPending || !hasConnection}
              >
                {testConnection.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                Test connection
              </Button>
            </div>
          )}

          {/* Whether the key is known-good, not merely whether one was typed. */}
          {config.last_error ? (
            <p className="flex items-start gap-2 text-[12.5px] text-destructive">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-none" />
              {config.last_error}
            </p>
          ) : config.last_validated_at ? (
            <p className="flex items-start gap-2 text-[12.5px] text-success">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 flex-none" />
              Connection verified on{' '}
              {new Date(config.last_validated_at).toLocaleString('en-US', {
                dateStyle: 'medium',
                timeStyle: 'short',
              })}
              .
            </p>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard title="How it's used">
        <ul className="space-y-2 text-[12.5px] text-muted-foreground">
          <li>
            Describe the page you want and the model drafts a complete layout, which then opens
            in the normal builder for you to edit.
          </li>
          <li>
            Generated markup is filtered before it is saved — scripts, embedded frames and inline
            event handlers are removed, so a draft can never carry code onto your public page.
          </li>
          <li>
            Forms are not generated. The draft marks where a form belongs and you drop a real one
            in from the builder's Forms tab, which is what makes submissions count as conversions.
          </li>
        </ul>
      </SectionCard>
    </div>
  );
}
