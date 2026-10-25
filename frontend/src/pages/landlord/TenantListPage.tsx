import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2 } from 'lucide-react';

import { Input } from '@/components/ui/input';
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
import { useTenants } from '@/hooks/useLandlord';
import { debounce } from '@/lib/utils';
import { cn } from '@/lib/utils';
import type { TenantListParams } from '@/types/landlord';

type ViewKey = 'all' | 'active' | 'suspended';

const VIEWS: Array<{ key: ViewKey; label: string }> = [
  { key: 'all', label: 'All tenants' },
  { key: 'active', label: 'Active' },
  { key: 'suspended', label: 'Suspended' },
];

const VIEW_PARAMS: Record<ViewKey, Partial<TenantListParams>> = {
  all: {},
  active: { status: 'active' },
  suspended: { status: 'suspended' },
};

const countFmt = (n: number) => new Intl.NumberFormat('en').format(n ?? 0);

export const TenantListPage = () => {
  const [view, setView] = useState<ViewKey>('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const params: TenantListParams = {
    ...VIEW_PARAMS[view],
    page,
    per_page: 25,
    ...(search ? { search } : {}),
  };

  const { tenants, total, totalPages, isLoading } = useTenants(params);

  // One cheap query per tile, reading only the total — same approach the
  // tenant-facing list screens use.
  const counts: Record<ViewKey, number> = {
    all: useTenants({ ...VIEW_PARAMS.all, page: 1, per_page: 1 }).total,
    active: useTenants({ ...VIEW_PARAMS.active, page: 1, per_page: 1 }).total,
    suspended: useTenants({ ...VIEW_PARAMS.suspended, page: 1, per_page: 1 }).total,
  };

  const onSearch = useMemo(
    () =>
      debounce((value: string) => {
        setSearch(value);
        setPage(1);
      }, 300),
    []
  );

  return (
    <div className="w-full space-y-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tenants</h1>
          <p className="text-[13px] text-muted-foreground">
            Every organization on the platform, with its plan and sending state.
          </p>
        </div>
      </div>

      <div className="grid gap-3.5 sm:grid-cols-3">
        {VIEWS.map((tile) => {
          const active = view === tile.key;
          return (
            <button
              key={tile.key}
              type="button"
              aria-pressed={active}
              onClick={() => {
                setView(tile.key);
                setPage(1);
              }}
              className={cn(
                'rounded-lg border bg-card p-4 text-left shadow-card transition-colors hover:border-brand/40',
                active && 'border-brand bg-brand/[.06]'
              )}
            >
              <span className="stat-label">{tile.label}</span>
              <p className="stat-value text-[22px]">{countFmt(counts[tile.key])}</p>
              <p className="delta">
                {active ? <b className="text-brand">Filtering</b> : <span>Click to filter</span>}
              </p>
            </button>
          );
        })}
      </div>

      <div className="overflow-hidden rounded-lg border bg-card shadow-card">
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <Input
            placeholder="Search by organization name…"
            onChange={(e) => onSearch(e.target.value)}
            className="h-8 max-w-xs flex-1"
          />
          {view !== 'all' && (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => {
                setView('all');
                setPage(1);
              }}
            >
              Clear filter
            </Button>
          )}
          <span className="ml-auto font-mono text-[11px] text-subtle-foreground">
            {countFmt(total)} shown
          </span>
        </div>

        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-11 w-full rounded-md" />
            ))}
          </div>
        ) : tenants.length === 0 ? (
          <div className="px-4 py-14 text-center">
            <Building2 className="mx-auto mb-3 h-6 w-6 text-subtle-foreground" />
            <h3 className="mb-1 text-[14px] font-semibold">
              {search || view !== 'all' ? 'No tenants match this view' : 'No tenants yet'}
            </h3>
            <p className="text-[12.5px] text-muted-foreground">
              {search || view !== 'all'
                ? 'Try clearing the search or the filter.'
                : 'Organizations appear here as customers register.'}
            </p>
          </div>
        ) : (
          <>
            {/* TableHead/TableCell carry px-0 with a pr-4 gutter, so the inset
                comes from here or the first column is clipped by the card. */}
            <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0 [&_tr>*:not(:first-child)]:whitespace-nowrap">
              <Table>
                <TableHeader>
                  <TableRow>
                    {/* Name absorbs the slack so the figures stay on one line. */}
                    <TableHead className="w-full">Organization</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead>State</TableHead>
                    <TableHead className="text-right">Users</TableHead>
                    <TableHead className="text-right">Contacts</TableHead>
                    {/* "Quota", not "Emails": this is the billing-month
                        counter against the plan limit, which is a different
                        figure from the overview's emails sent in a period. */}
                    <TableHead className="text-right">Quota</TableHead>
                    <TableHead className="text-right">Bounce</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenants.map((t) => {
                    const overQuota = t.emails_limit > 0 && t.emails_used >= t.emails_limit;
                    return (
                      <TableRow key={t.id}>
                        <TableCell>
                          <Link
                            to={`/landlord/tenants/${t.id}`}
                            className="font-medium text-foreground hover:text-brand"
                          >
                            {t.name}
                          </Link>
                          <span className="ml-2 font-mono text-[11px] text-subtle-foreground">
                            {t.slug}
                          </span>
                        </TableCell>
                        <TableCell className="font-mono text-[11.5px] uppercase">
                          {t.plan}
                        </TableCell>
                        <TableCell>
                          {!t.is_active ? (
                            <span className="rounded bg-destructive/[.14] px-1.5 py-0.5 text-[11px] font-medium text-destructive">
                              Suspended
                            </span>
                          ) : t.sending_paused ? (
                            <span className="rounded bg-warning/[.14] px-1.5 py-0.5 text-[11px] font-medium text-warning">
                              Sending paused
                            </span>
                          ) : (
                            <span className="rounded bg-success/[.14] px-1.5 py-0.5 text-[11px] font-medium text-success">
                              Active
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{t.users}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {countFmt(t.contacts)}
                        </TableCell>
                        <TableCell
                          className={cn('text-right tabular-nums', overQuota && 'text-destructive')}
                        >
                          {countFmt(t.emails_used)}
                          {t.emails_limit > 0 && (
                            <span className="text-subtle-foreground">
                              {' / '}
                              {countFmt(t.emails_limit)}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {t.bounce_rate_30d === null ? (
                            <span className="text-subtle-foreground">—</span>
                          ) : (
                            `${t.bounce_rate_30d}%`
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            {totalPages > 1 && (
              <div className="flex flex-wrap items-center justify-between gap-2 border-t px-3 py-2.5">
                <span className="font-mono text-[11px] text-subtle-foreground">
                  {(page - 1) * 25 + 1}–{Math.min(page * 25, total)} of {countFmt(total)}
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8"
                    onClick={() => setPage(page - 1)}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  <span className="px-2 font-mono text-[11px] text-muted-foreground">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8"
                    onClick={() => setPage(page + 1)}
                    disabled={page === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
