import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Copy,
  Globe,
  Loader2,
  Plus,
  RefreshCw,
  Send,
  Shield,
  Trash2,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { useEmailConfig, useSendingDomains, useEmailConfigMutations } from '@/hooks/useEmailConfig';
import type { EmailProvider, UpdateEmailConfigData } from '@/types/emailConfig';

const PROVIDER_LABELS: Record<EmailProvider, string> = {
  platform_default: 'Platform Default (shared SMTP)',
  smtp: 'Custom SMTP',
  sendgrid: 'SendGrid',
  mailgun: 'Mailgun',
  ses: 'Amazon SES',
};

const DOMAIN_STATUS_CONFIG = {
  pending: { label: 'Pending', color: 'bg-yellow-100 text-yellow-700', icon: RefreshCw },
  verified: { label: 'Verified', color: 'bg-green-100 text-green-700', icon: CheckCircle2 },
  failed: { label: 'Failed', color: 'bg-red-100 text-red-700', icon: XCircle },
};

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

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="text-blue-500 hover:text-blue-700 flex items-center gap-1 text-xs"
    >
      <Copy className="h-3 w-3" />
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

export function EmailTab() {
  const { data: config, isLoading } = useEmailConfig();
  const { data: domains = [] } = useSendingDomains();
  const { updateConfig, testConnection, resumeSending, addDomain, verifyDomain, deleteDomain } =
    useEmailConfigMutations();

  // Local form state
  const [identity, setIdentity] = useState({ from_name: '', from_email: '', reply_to_email: '' });
  const [provider, setProvider] = useState<EmailProvider>('platform_default');
  const [smtp, setSmtp] = useState({
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    smtp_use_tls: true,
    smtp_use_ssl: false,
  });
  const [apiKey, setApiKey] = useState('');
  const [providerDomain, setProviderDomain] = useState('');
  const [providerRegion, setProviderRegion] = useState('us-east-1');
  const [compliance, setCompliance] = useState({
    physical_address: '',
    email_footer_text: '',
    unsubscribe_redirect_url: '',
  });
  const [limits, setLimits] = useState({
    daily_send_limit: 0,
    hourly_send_limit: 0,
    bounce_threshold_pct: '5.00',
    complaint_threshold_pct: '0.10',
  });
  const [testEmail, setTestEmail] = useState('');
  const [newDomain, setNewDomain] = useState('');

  // Sync config into form state
  useEffect(() => {
    if (!config) return;
    setIdentity({
      from_name: config.from_name,
      from_email: config.from_email,
      reply_to_email: config.reply_to_email,
    });
    setProvider(config.provider);
    setSmtp({
      smtp_host: config.smtp_host,
      smtp_port: config.smtp_port,
      smtp_username: config.smtp_username,
      smtp_password: '',  // never pre-fill password
      smtp_use_tls: config.smtp_use_tls,
      smtp_use_ssl: config.smtp_use_ssl,
    });
    setProviderDomain(config.provider_domain);
    setProviderRegion(config.provider_region);
    setCompliance({
      physical_address: config.physical_address,
      email_footer_text: config.email_footer_text,
      unsubscribe_redirect_url: config.unsubscribe_redirect_url,
    });
    setLimits({
      daily_send_limit: config.daily_send_limit,
      hourly_send_limit: config.hourly_send_limit,
      bounce_threshold_pct: config.bounce_threshold_pct,
      complaint_threshold_pct: config.complaint_threshold_pct,
    });
  }, [config]);

  const handleSaveIdentity = async () => {
    await updateConfig.mutateAsync(identity);
    toast.success('Sending identity saved.');
  };

  const handleSaveProvider = async () => {
    const payload: UpdateEmailConfigData = { provider };
    if (provider === 'smtp') {
      Object.assign(payload, smtp);
    } else if (provider === 'sendgrid' || provider === 'mailgun') {
      if (apiKey) payload.api_key = apiKey;
      if (providerDomain) payload.provider_domain = providerDomain;
    } else if (provider === 'ses') {
      if (apiKey) payload.api_key = apiKey;
      payload.provider_region = providerRegion;
    }
    await updateConfig.mutateAsync(payload);
    toast.success('Provider configuration saved.');
  };

  const handleSaveCompliance = async () => {
    await updateConfig.mutateAsync(compliance);
    toast.success('Compliance settings saved.');
  };

  const handleSaveLimits = async () => {
    await updateConfig.mutateAsync(limits);
    toast.success('Limits saved.');
  };

  const handleTest = async () => {
    if (!testEmail) return;
    const result = await testConnection.mutateAsync(testEmail);
    if (result.success) {
      toast.success(result.message);
    } else {
      toast.error(result.message);
    }
  };

  const handleAddDomain = async () => {
    if (!newDomain.trim()) return;
    await addDomain.mutateAsync(newDomain.trim());
    setNewDomain('');
    toast.success('Domain added. Copy the DNS records below and then verify.');
  };

  const handleVerifyDomain = async (id: string) => {
    const result = await verifyDomain.mutateAsync(id);
    if (result.success) {
      toast.success(result.message);
    } else {
      toast.error(result.message);
    }
  };

  const handleDeleteDomain = async (id: string) => {
    if (!confirm('Remove this domain?')) return;
    await deleteDomain.mutateAsync(id);
    toast.success('Domain removed.');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">

      {/* Threshold pause alert */}
      {config?.sending_paused_due_to_threshold && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
          <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-red-800">Sending paused</p>
            <p className="text-sm text-red-600 mt-0.5">
              Bounce or complaint rate exceeded the configured threshold. Review your list quality
              before resuming.
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="border-red-300 text-red-700 hover:bg-red-100 flex-shrink-0"
            onClick={() => resumeSending.mutateAsync()}
          >
            Resume Sending
          </Button>
        </div>
      )}

      {/* ── 1. Sending Identity ─────────────────────────────────────────────── */}
      <SectionCard
        title="Sending Identity"
        description="Default From name and address used across campaigns, sequences, and workflows."
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>From Name</Label>
            <Input
              value={identity.from_name}
              onChange={(e) => setIdentity({ ...identity, from_name: e.target.value })}
              placeholder="Your Company"
            />
          </div>
          <div>
            <Label>From Email</Label>
            <Input
              type="email"
              value={identity.from_email}
              onChange={(e) => setIdentity({ ...identity, from_email: e.target.value })}
              placeholder="hello@yourcompany.com"
            />
          </div>
          <div className="col-span-2">
            <Label>Reply-To Email <span className="text-gray-400 font-normal">(optional)</span></Label>
            <Input
              type="email"
              value={identity.reply_to_email}
              onChange={(e) => setIdentity({ ...identity, reply_to_email: e.target.value })}
              placeholder="Leave blank to use From Email"
            />
          </div>
        </div>
        <div className="flex justify-end mt-4">
          <Button onClick={handleSaveIdentity} disabled={updateConfig.isPending}>
            {updateConfig.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Save Identity
          </Button>
        </div>
      </SectionCard>

      {/* ── 2. Provider / SMTP ──────────────────────────────────────────────── */}
      <SectionCard
        title="Email Provider"
        description="Choose how emails are sent. Custom providers give you better deliverability and branding."
      >
        <div className="space-y-4">
          <div>
            <Label>Provider</Label>
            <Select value={provider} onValueChange={(v) => setProvider(v as EmailProvider)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.entries(PROVIDER_LABELS) as [EmailProvider, string][]).map(([val, label]) => (
                  <SelectItem key={val} value={val}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {provider === 'platform_default' && (
            <p className="text-sm text-gray-500 bg-gray-50 p-3 rounded-lg">
              Emails are sent through the platform's shared SMTP server. For production use, configure
              your own provider for better deliverability and branding.
            </p>
          )}

          {provider === 'smtp' && (
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>SMTP Host</Label>
                <Input
                  value={smtp.smtp_host}
                  onChange={(e) => setSmtp({ ...smtp, smtp_host: e.target.value })}
                  placeholder="smtp.yourprovider.com"
                />
              </div>
              <div>
                <Label>Port</Label>
                <Input
                  type="number"
                  value={smtp.smtp_port}
                  onChange={(e) => setSmtp({ ...smtp, smtp_port: parseInt(e.target.value) || 587 })}
                />
              </div>
              <div>
                <Label>Username</Label>
                <Input
                  value={smtp.smtp_username}
                  onChange={(e) => setSmtp({ ...smtp, smtp_username: e.target.value })}
                  autoComplete="off"
                />
              </div>
              <div className="col-span-2">
                <Label>
                  Password{' '}
                  {config?.smtp_password_set && (
                    <span className="text-xs text-gray-400 font-normal">(saved — leave blank to keep)</span>
                  )}
                </Label>
                <Input
                  type="password"
                  value={smtp.smtp_password}
                  onChange={(e) => setSmtp({ ...smtp, smtp_password: e.target.value })}
                  autoComplete="new-password"
                  placeholder={config?.smtp_password_set ? '••••••••' : 'Enter password'}
                />
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={smtp.smtp_use_tls}
                  onCheckedChange={(v) => setSmtp({ ...smtp, smtp_use_tls: v, smtp_use_ssl: v ? false : smtp.smtp_use_ssl })}
                />
                <Label>Use TLS (port 587)</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={smtp.smtp_use_ssl}
                  onCheckedChange={(v) => setSmtp({ ...smtp, smtp_use_ssl: v, smtp_use_tls: v ? false : smtp.smtp_use_tls })}
                />
                <Label>Use SSL (port 465)</Label>
              </div>
            </div>
          )}

          {(provider === 'sendgrid' || provider === 'mailgun') && (
            <div className="space-y-3">
              <div>
                <Label>
                  API Key{' '}
                  {config?.api_key_set && (
                    <span className="text-xs text-gray-400 font-normal">(saved — leave blank to keep)</span>
                  )}
                </Label>
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={config?.api_key_set ? '••••••••' : 'Paste your API key'}
                />
              </div>
              {provider === 'mailgun' && (
                <div>
                  <Label>Mailgun Domain</Label>
                  <Input
                    value={providerDomain}
                    onChange={(e) => setProviderDomain(e.target.value)}
                    placeholder="mg.yourcompany.com"
                  />
                </div>
              )}
            </div>
          )}

          {provider === 'ses' && (
            <div className="space-y-3">
              <div>
                <Label>
                  SMTP Credentials{' '}
                  <span className="text-xs text-gray-400 font-normal">(format: SMTP_USER::SMTP_PASS)</span>
                </Label>
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={config?.api_key_set ? '••••••••' : 'AKIAIOSFODNN7EXAMPLE::wJalrXUtn...'}
                />
              </div>
              <div>
                <Label>AWS Region</Label>
                <Select value={providerRegion} onValueChange={setProviderRegion}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {['us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-southeast-1', 'ap-northeast-1'].map((r) => (
                      <SelectItem key={r} value={r}>{r}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <div className="flex items-end justify-between pt-2">
            {/* Test email */}
            <div className="flex items-end gap-2">
              <div>
                <Label className="text-xs text-gray-500">Send test email to</Label>
                <Input
                  type="email"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-52"
                />
              </div>
              <Button
                variant="outline"
                onClick={handleTest}
                disabled={!testEmail || testConnection.isPending}
              >
                {testConnection.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                Test
              </Button>
            </div>
            <Button onClick={handleSaveProvider} disabled={updateConfig.isPending}>
              {updateConfig.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save Provider
            </Button>
          </div>
        </div>
      </SectionCard>

      {/* ── 3. Domain Authentication ────────────────────────────────────────── */}
      <SectionCard
        title="Domain Authentication"
        description="Add sending domains and configure SPF/DKIM records for better deliverability."
      >
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              placeholder="mail.yourcompany.com"
              onKeyDown={(e) => e.key === 'Enter' && handleAddDomain()}
            />
            <Button
              variant="outline"
              onClick={handleAddDomain}
              disabled={!newDomain.trim() || addDomain.isPending}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Domain
            </Button>
          </div>

          {domains.length === 0 ? (
            <div className="text-center py-8 border-2 border-dashed rounded-lg text-gray-400 text-sm">
              <Globe className="h-8 w-8 mx-auto mb-2 opacity-50" />
              No domains added yet. Add a domain to set up SPF/DKIM authentication.
            </div>
          ) : (
            <div className="space-y-3">
              {domains.map((d) => {
                const sc = DOMAIN_STATUS_CONFIG[d.status];
                const StatusIcon = sc.icon;
                return (
                  <Collapsible key={d.id}>
                    <div className="border rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-3 bg-gray-50">
                        <div className="flex items-center gap-3">
                          <span className="font-medium text-sm">{d.domain}</span>
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${sc.color}`}>
                            <StatusIcon className="h-3 w-3" />
                            {sc.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CollapsibleTrigger asChild>
                            <Button variant="ghost" size="sm" className="text-xs gap-1">
                              DNS Records <ChevronDown className="h-3 w-3" />
                            </Button>
                          </CollapsibleTrigger>
                          {d.status !== 'verified' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleVerifyDomain(d.id)}
                              disabled={verifyDomain.isPending}
                            >
                              <RefreshCw className={`h-3 w-3 mr-1 ${verifyDomain.isPending ? 'animate-spin' : ''}`} />
                              Verify
                            </Button>
                          )}
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8 text-red-500 hover:text-red-600"
                            onClick={() => handleDeleteDomain(d.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      <CollapsibleContent>
                        <div className="px-4 pb-4 pt-3 space-y-3 bg-white border-t">
                          {/* SPF */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">SPF Record (TXT)</span>
                              <CopyButton value={d.spf_record} />
                            </div>
                            <p className="text-xs text-gray-400 mb-1">Add to: <code className="bg-gray-100 px-1 rounded">{d.domain}</code></p>
                            <code className="block text-xs bg-gray-100 rounded p-2 break-all">{d.spf_record || '—'}</code>
                          </div>
                          {/* DKIM */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">DKIM Record (TXT)</span>
                              <CopyButton value={d.dkim_record_value} />
                            </div>
                            <p className="text-xs text-gray-400 mb-1">
                              Add to: <code className="bg-gray-100 px-1 rounded">{d.dkim_record_name || `${d.dkim_selector}._domainkey.${d.domain}`}</code>
                            </p>
                            <code className="block text-xs bg-gray-100 rounded p-2 break-all">{d.dkim_record_value || '—'}</code>
                          </div>
                          {d.last_check_error && (
                            <p className="text-xs text-red-500">{d.last_check_error}</p>
                          )}
                        </div>
                      </CollapsibleContent>
                    </div>
                  </Collapsible>
                );
              })}
            </div>
          )}
        </div>
      </SectionCard>

      {/* ── 4. Compliance ───────────────────────────────────────────────────── */}
      <SectionCard
        title="Compliance"
        description="CAN-SPAM requires a physical mailing address in every email. GDPR recommends a clear unsubscribe path."
      >
        <div className="space-y-4">
          <div>
            <Label>Physical Mailing Address <span className="text-red-500">*</span></Label>
            <Textarea
              value={compliance.physical_address}
              onChange={(e) => setCompliance({ ...compliance, physical_address: e.target.value })}
              placeholder="123 Main St, City, State 12345, USA"
              rows={2}
            />
            <p className="text-xs text-gray-400 mt-1">Required by CAN-SPAM. Appended to every email.</p>
          </div>
          <div>
            <Label>Email Footer Text <span className="text-gray-400 font-normal">(optional)</span></Label>
            <Textarea
              value={compliance.email_footer_text}
              onChange={(e) => setCompliance({ ...compliance, email_footer_text: e.target.value })}
              placeholder="© 2025 Your Company. All rights reserved."
              rows={2}
            />
          </div>
          <div>
            <Label>Custom Unsubscribe Redirect URL <span className="text-gray-400 font-normal">(optional)</span></Label>
            <Input
              type="url"
              value={compliance.unsubscribe_redirect_url}
              onChange={(e) => setCompliance({ ...compliance, unsubscribe_redirect_url: e.target.value })}
              placeholder="https://yoursite.com/goodbye (leave blank for platform default)"
            />
          </div>
          <div className="flex justify-end">
            <Button onClick={handleSaveCompliance} disabled={updateConfig.isPending}>
              Save Compliance
            </Button>
          </div>
        </div>
      </SectionCard>

      {/* ── 5. Limits & Thresholds ──────────────────────────────────────────── */}
      <SectionCard
        title="Sending Limits & Thresholds"
        description="Cap email volume and auto-pause if bounce or complaint rates spike."
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Daily Send Limit</Label>
              <Input
                type="number"
                min={0}
                value={limits.daily_send_limit}
                onChange={(e) => setLimits({ ...limits, daily_send_limit: parseInt(e.target.value) || 0 })}
              />
              <p className="text-xs text-gray-400 mt-1">0 = unlimited</p>
            </div>
            <div>
              <Label>Hourly Send Limit</Label>
              <Input
                type="number"
                min={0}
                value={limits.hourly_send_limit}
                onChange={(e) => setLimits({ ...limits, hourly_send_limit: parseInt(e.target.value) || 0 })}
              />
              <p className="text-xs text-gray-400 mt-1">0 = unlimited</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 pt-2 border-t">
            <div>
              <Label className="flex items-center gap-1">
                <Shield className="h-3 w-3 text-orange-500" />
                Bounce Rate Threshold (%)
              </Label>
              <Input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={limits.bounce_threshold_pct}
                onChange={(e) => setLimits({ ...limits, bounce_threshold_pct: e.target.value })}
              />
              <p className="text-xs text-gray-400 mt-1">Auto-pauses sending if exceeded</p>
            </div>
            <div>
              <Label className="flex items-center gap-1">
                <Shield className="h-3 w-3 text-red-500" />
                Complaint Rate Threshold (%)
              </Label>
              <Input
                type="number"
                min={0}
                max={100}
                step={0.01}
                value={limits.complaint_threshold_pct}
                onChange={(e) => setLimits({ ...limits, complaint_threshold_pct: e.target.value })}
              />
              <p className="text-xs text-gray-400 mt-1">Auto-pauses sending if exceeded</p>
            </div>
          </div>
          <p className="text-xs text-gray-400 bg-amber-50 border border-amber-100 rounded p-2">
            Industry standards: keep bounce rate below 2% and complaint rate below 0.08% to maintain good deliverability.
          </p>

          <div className="flex justify-end">
            <Button onClick={handleSaveLimits} disabled={updateConfig.isPending}>
              Save Limits
            </Button>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
