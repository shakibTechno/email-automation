import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useDeliverability } from '@/hooks/useLandlord';
import { formatDateTime } from '@/lib/utils';
import { cn } from '@/lib/utils';
import type { DeliverabilityRow } from '@/types/landlord';

type ViewKey = 'all' | 'over_threshold' | 'held' | 'unverified';

const VIEWS: Array<{ key: ViewKey; label: string; hint: string; test: (r: DeliverabilityRow) => boolean }> = [
  { key: 'all', label: 'Sending tenants', hint: 'with a mail server tenant', test: () => true },
  {
    key: 'over_threshold',
    label: 'Over threshold',
    hint: 'bouncing above their limit',
    test: (r) => r.over_threshold,
  },
  {
    key: 'held',
    label: 'Mail held',
    hint: 'stuck until someone acts',
    test: (r) => r.held > 0,
  },
  {
    key: 'unverified',
    label: 'Unverified domains',
    hint: 'added but never verified',
    test: (r) => r.unverified_domains > 0,
  },
];

const full = (n: number) => new Intl.NumberFormat('en').format(n ?? 0);

export const DeliverabilityPage = () => {
  const [view, setView] = useState<ViewKey>('all');
  const { data, isLoading } = useDeliverability();

  const rows = useMemo(() => data?.results ?? [], [data]);
  const counts = useMemo(
    () =>
      VIEWS.reduce(
        (acc, v) => ({ ...acc, [v.key]: rows.filter(v.test).length }),
        {} as Record<ViewKey, number>
      ),
    [rows]
  );

  const active = VIEWS.find((v) => v.key === view)!;
  const visible = rows.filter(active.test);

  return (
    <div className="w-full space-y-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Deliverability</h1>
          {/* The reason this screen exists, said plainly: the blast radius of
              one bad tenant is every other tenant. */}
          <p className="text-[13px] text-muted-foreground">
            Every tenant sends from the same IP, so one tenant's bounce rate is everyone's
            reputation. Ranked by risk to the shared IP.
          </p>
        </div>
      </div>

      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
        {VIEWS.map((tile) => {
          const selected = view === tile.key;
          const danger = tile.key !== 'all' && counts[tile.key] > 0;
          return (
            <button
              key={tile.key}
              type="button"
              aria-pressed={selected}
              onClick={() => setView(tile.key)}
              className={cn(
                'rounded-lg border bg-card p-4 text-left shadow-card transition-colors hover:border-brand/40',
                selected && 'border-brand bg-brand/[.06]'
              )}
            >
              <span className="stat-label">{tile.label}</span>
              <p
                className={cn(
                  'stat-value text-[22px]',
                  danger && tile.key === 'over_threshold' && 'text-destructive',
                  danger && tile.key !== 'over_threshold' && 'text-warning'
                )}
              >
                {counts[tile.key] ?? 0}
              </p>
              <p className="delta">
                {selected ? <b className="text-brand">Filtering</b> : <span>{tile.hint}</span>}
              </p>
            </button>
          );
        })}
      </div>

      <div className="overflow-hidden rounded-lg border bg-card shadow-card">
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <h2 className="text-[13.5px] font-semibold">{active.label}</h2>
          {view !== 'all' && (
            <Button variant="outline" size="sm" className="h-8" onClick={() => setView('all')}>
              Clear filter
            </Button>
          )}
          <span className="ml-auto font-mono text-[11px] text-subtle-foreground">
            {visible.length} of {rows.length}
          </span>
        </div>

        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-11 w-full rounded-md" />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <div className="px-4 py-14 text-center">
            <ShieldCheck className="mx-auto mb-3 h-6 w-6 text-success" />
            <h3 className="mb-1 text-[14px] font-semibold">
              {view === 'all' ? 'No tenants are sending yet' : 'Nothing in this category'}
            </h3>
            <p className="text-[12.5px] text-muted-foreground">
              {view === 'all'
                ? 'Tenants appear here once a mail server tenant is provisioned for them.'
                : 'Good — the shared IP is not at risk from this.'}
            </p>
          </div>
        ) : (
          <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0 [&_tr>*:not(:first-child)]:whitespace-nowrap">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-full">Tenant</TableHead>
                  <TableHead className="text-right">Bounce (30d)</TableHead>
                  <TableHead className="text-right">Sent / hr</TableHead>
                  <TableHead className="text-right">Queued</TableHead>
                  <TableHead className="text-right">Held</TableHead>
                  <TableHead className="text-right">Unverified</TableHead>
                  <TableHead>Mail state</TableHead>
                  <TableHead className="text-right">Synced</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((r) => (
                  <TableRow
                    key={r.organization_id}
                    className={cn(r.over_threshold && 'bg-destructive/[.04]')}
                  >
                    <TableCell>
                      <Link
                        to={`/landlord/tenants/${r.organization_id}`}
                        className="font-medium text-foreground hover:text-brand"
                      >
                        {r.organization_name}
                      </Link>
                      <span className="ml-2 font-mono text-[11px] uppercase text-subtle-foreground">
                        {r.plan}
                      </span>
                    </TableCell>
                    <TableCell
                      className={cn(
                        'text-right tabular-nums',
                        r.over_threshold && 'font-semibold text-destructive'
                      )}
                    >
                      {r.bounce_rate_30d}%
                      <span className="text-subtle-foreground">
                        {' / '}
                        {r.bounce_threshold}%
                      </span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {full(r.sent_last_hour)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{full(r.queued)}</TableCell>
                    <TableCell
                      className={cn(
                        'text-right tabular-nums',
                        r.held > 0 && 'font-semibold text-warning'
                      )}
                    >
                      {full(r.held)}
                    </TableCell>
                    <TableCell
                      className={cn(
                        'text-right tabular-nums',
                        r.unverified_domains > 0 && 'text-warning'
                      )}
                    >
                      {r.unverified_domains || '—'}
                    </TableCell>
                    <TableCell>
                      {!r.is_active ? (
                        <span className="rounded bg-destructive/[.14] px-1.5 py-0.5 text-[11px] font-medium text-destructive">
                          Account suspended
                        </span>
                      ) : r.sending_paused || r.mail_status !== 'active' ? (
                        <span
                          className="rounded bg-warning/[.14] px-1.5 py-0.5 text-[11px] font-medium text-warning"
                          title={r.suspension_reason || undefined}
                        >
                          {r.sending_paused ? 'Sending paused' : r.mail_status}
                        </span>
                      ) : (
                        <span className="rounded bg-success/[.14] px-1.5 py-0.5 text-[11px] font-medium text-success">
                          Sending
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono text-[11px] text-subtle-foreground">
                      {r.last_synced_at ? formatDateTime(r.last_synced_at) : 'never'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        <div className="border-t px-3 py-2.5 text-[11.5px] text-muted-foreground">
          Bounce rate, queue and hold counts come from the mail server's hourly sync, so they lag
          by up to an hour. A tenant's own page recomputes them live.
        </div>
      </div>
    </div>
  );
};
