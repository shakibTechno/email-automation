import { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Copy,
  Globe,
  Loader2,
  RefreshCw,
  Star,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useLandingDomains, useLandingDomainActions } from '@/hooks/useLandingDomains';
import { formatDateTime } from '@/lib/utils';
import { cn } from '@/lib/utils';
import type { LandingDomain } from '@/types/landing-page';

const CopyButton = ({ value, label }: { value: string; label: string }) => (
  <button
    type="button"
    onClick={() => {
      navigator.clipboard.writeText(value);
      toast.success(`${label} copied.`);
    }}
    className="rounded p-1 text-subtle-foreground transition-colors hover:bg-accent hover:text-foreground"
    title={`Copy ${label.toLowerCase()}`}
  >
    <Copy className="h-3.5 w-3.5" />
  </button>
);

const StatusPill = ({ domain }: { domain: LandingDomain }) => {
  if (domain.is_verified) {
    return (
      <span className="flex items-center gap-1 rounded bg-success/[.14] px-1.5 py-0.5 text-[11px] font-medium text-success">
        <CheckCircle2 className="h-3 w-3" />
        Live
      </span>
    );
  }
  if (domain.status === 'failed') {
    return (
      <span className="flex items-center gap-1 rounded bg-warning/[.14] px-1.5 py-0.5 text-[11px] font-medium text-warning">
        <AlertTriangle className="h-3 w-3" />
        Not ready
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground">
      <Clock className="h-3 w-3" />
      Waiting for DNS
    </span>
  );
};

const DomainCard = ({ domain }: { domain: LandingDomain }) => {
  const { verify, setPrimary, disconnect, isBusy } = useLandingDomainActions();
  const [confirmRemove, setConfirmRemove] = useState(false);
  const record = domain.dns_record;

  return (
    <div className="rounded-lg border bg-card p-4 shadow-card">
      <div className="flex flex-wrap items-center gap-2">
        <Globe className="h-4 w-4 flex-none text-subtle-foreground" />
        <span className="font-mono text-[13.5px] font-medium">{domain.domain}</span>
        <StatusPill domain={domain} />
        {domain.is_primary && (
          <span className="flex items-center gap-1 rounded bg-brand/[.12] px-1.5 py-0.5 text-[11px] font-medium text-brand">
            <Star className="h-3 w-3" />
            Default
          </span>
        )}

        <div className="ml-auto flex items-center gap-1.5">
          <Button
            variant="outline"
            size="sm"
            className="h-8"
            disabled={isBusy}
            onClick={() => verify.mutate(domain.id)}
          >
            {verify.isPending ? (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            )}
            Check now
          </Button>
          {!domain.is_primary && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8"
              disabled={isBusy}
              onClick={() => setPrimary.mutate(domain.id)}
            >
              Make default
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-muted-foreground hover:text-destructive"
            disabled={isBusy}
            onClick={() => setConfirmRemove(true)}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* The record to publish stays visible after verification: a customer who
          changes DNS providers needs it again, and hiding it would mean
          disconnecting the domain just to read it. */}
      <div className="mt-3 overflow-hidden rounded-md border bg-muted/40">
        <div className="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-1 p-3 text-[12.5px]">
          <span className="stat-label">Type</span>
          <span className="font-mono">{record?.type ?? 'CNAME'}</span>
          <span />

          <span className="stat-label">Host</span>
          <span className="truncate font-mono">{record?.host ?? domain.domain}</span>
          <CopyButton value={record?.host ?? domain.domain} label="Host" />

          <span className="stat-label">Points to</span>
          <span className="truncate font-mono">
            {record?.value || (
              <span className="text-muted-foreground">
                Ask your administrator for the target hostname
              </span>
            )}
          </span>
          {record?.value ? <CopyButton value={record.value} label="Target" /> : <span />}
        </div>
      </div>

      {!domain.is_verified && domain.last_check_error && (
        <p className="mt-2 text-[12px] text-warning">{domain.last_check_error}</p>
      )}

      <p className="mt-2 flex flex-wrap gap-x-3 text-[11.5px] text-subtle-foreground">
        <span>
          {domain.page_count} {domain.page_count === 1 ? 'page' : 'pages'}
        </span>
        {domain.last_check_at && <span>checked {formatDateTime(domain.last_check_at)}</span>}
        {domain.verified_at && <span>live since {formatDateTime(domain.verified_at)}</span>}
      </p>

      <AlertDialog open={confirmRemove} onOpenChange={setConfirmRemove}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {domain.domain}?</AlertDialogTitle>
            <AlertDialogDescription>
              Pages served from this domain go back to their address on the platform. Nothing
              is deleted, but any link you have already shared on this domain will stop
              working.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => disconnect.mutate(domain.id)}
            >
              Remove domain
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export function DomainsTab() {
  const { domains, isLoading } = useLandingDomains();
  const { connect, isBusy } = useLandingDomainActions();
  const [value, setValue] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const domain = value.trim();
    if (!domain) return;
    connect.mutate(domain, { onSuccess: () => setValue('') });
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[15px] font-semibold">Landing page domains</h2>
        <p className="text-[13px] text-muted-foreground">
          Serve your landing pages from your own domain, so a campaign link reads{' '}
          <span className="font-mono text-[12px]">go.yourbrand.com/black-friday</span>. Pages
          keep working on their platform address until a domain goes live.
        </p>
      </div>

      <form onSubmit={submit} className="rounded-lg border bg-card p-4 shadow-card">
        <Label htmlFor="new-domain" className="text-[12.5px]">
          Add a domain
        </Label>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <Input
            id="new-domain"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="go.yourbrand.com"
            className="h-9 max-w-sm flex-1 font-mono text-[13px]"
          />
          <Button type="submit" size="sm" className="h-9" disabled={isBusy || !value.trim()}>
            {connect.isPending ? 'Adding…' : 'Add domain'}
          </Button>
        </div>
        {/* Stated up front rather than discovered after a failed check: an apex
            domain cannot carry a CNAME, and that is the most common mistake. */}
        <p className="mt-2 text-[11.5px] text-muted-foreground">
          Use a subdomain such as <span className="font-mono">go.</span> or{' '}
          <span className="font-mono">pages.</span> — a bare domain like{' '}
          <span className="font-mono">yourbrand.com</span> cannot point here with a CNAME
          record. The HTTPS certificate is issued automatically once the record is live.
        </p>
      </form>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-36 w-full rounded-lg" />
          <Skeleton className="h-36 w-full rounded-lg" />
        </div>
      ) : domains.length === 0 ? (
        <div className="rounded-lg border bg-card px-4 py-14 text-center shadow-card">
          <Globe className="mx-auto mb-3 h-6 w-6 text-subtle-foreground" />
          <h3 className="mb-1 text-[14px] font-semibold">No domains connected</h3>
          <p className="text-[12.5px] text-muted-foreground">
            Your landing pages are currently served from the platform's address.
          </p>
        </div>
      ) : (
        <div className={cn('space-y-3')}>
          {domains.map((domain) => (
            <DomainCard key={domain.id} domain={domain} />
          ))}
        </div>
      )}
    </div>
  );
}
