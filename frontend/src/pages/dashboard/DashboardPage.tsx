import { useState } from 'react';
import { Link } from 'react-router-dom';
import { format, formatDistanceToNowStrict, parseISO } from 'date-fns';
import { ArrowRight, Plus, RefreshCw } from 'lucide-react';

import { useDashboard } from '@/hooks/useDashboard';
import { usePermissions } from '@/hooks/usePermissions';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { StatTile } from '@/components/dashboard/StatTile';
import { TickBars } from '@/components/dashboard/charts';
import { AlertsCard } from '@/components/dashboard/AlertsCard';
import { AssignedToMe } from '@/components/dashboard/AssignedToMe';
import { UpcomingWeek } from '@/components/dashboard/UpcomingWeek';
import { cn } from '@/lib/utils';
import type { DashboardTile } from '@/types/dashboard';

const RANGES = [7, 30, 90] as const;

/** Every quick action is a permission someone might not have. */
const QUICK_ACTIONS = [
  { label: 'Campaign', to: '/campaigns/new', permission: 'campaigns.create' },
  { label: 'Contact', to: '/contacts/new', permission: 'contacts.create' },
  { label: 'Form', to: '/forms/new', permission: 'forms.create' },
  { label: 'Landing page', to: '/landing-pages', permission: 'landing_pages.create' },
];

function tileValue(tile: DashboardTile): string {
  if (tile.unit === '%') return `${tile.value}%`;
  return tile.value > 0 ? `+${tile.value.toLocaleString()}` : tile.value.toLocaleString();
}

function relative(iso: string): string {
  try {
    return formatDistanceToNowStrict(parseISO(iso), { addSuffix: true });
  } catch {
    return '';
  }
}

export function DashboardPage() {
  const [days, setDays] = useState<number>(30);
  const { data, isLoading, isError, refetch } = useDashboard(days);
  const { can } = usePermissions();

  const todayKey = format(new Date(), 'yyyy-MM-dd');
  const actions = QUICK_ACTIONS.filter((a) => can(a.permission));

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3.5">
        <Skeleton className="h-16 w-72" />
        <Skeleton className="h-[120px] w-full rounded-lg" />
        <Skeleton className="h-[200px] w-full rounded-lg" />
        <Skeleton className="h-[140px] w-full rounded-lg" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-lg border border-dashed p-10 text-center">
        <h3 className="text-[15px] font-semibold">Could not load your dashboard</h3>
        <p className="mt-1 text-sm text-muted-foreground">Try again in a moment.</p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Retry
        </Button>
      </div>
    );
  }

  const nothingVisible =
    data.tiles.length === 0 &&
    data.alerts.length === 0 &&
    !data.upcoming &&
    !data.assigned &&
    !data.recent_campaigns &&
    !data.recent_submissions;

  return (
    <div className="flex flex-col gap-3.5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
          <p className="text-[13px] text-muted-foreground">
            {data.alerts.length > 0
              ? `${data.alerts.length} thing${data.alerts.length === 1 ? '' : 's'} need${
                  data.alerts.length === 1 ? 's' : ''
                } you.`
              : 'Nothing needs you right now. Here is what is yours and what is coming.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 rounded-md border bg-card p-0.5">
            {RANGES.map((r) => (
              <button
                key={r}
                type="button"
                aria-pressed={days === r}
                onClick={() => setDays(r)}
                className={cn(
                  'rounded-[6px] px-2.5 py-1 font-mono text-[11px] transition-colors',
                  days === r
                    ? 'bg-brand-fill text-brand-ink'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {r}d
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => refetch()}
            className="grid h-8 w-8 place-items-center rounded-md border bg-card text-muted-foreground hover:text-foreground"
            aria-label="Refresh"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>

          {actions.map((a) => (
            <Button key={a.to} variant="outline" size="sm" asChild>
              <Link to={a.to}>
                <Plus className="h-3.5 w-3.5" /> {a.label}
              </Link>
            </Button>
          ))}
        </div>
      </div>

      {nothingVisible && (
        <div className="rounded-lg border border-dashed p-10 text-center">
          <p className="font-medium">Nothing here for your role</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
            The dashboard shows campaigns, sequences, forms and CRM work. Your
            role reaches none of those, so there is nothing to put on it.
          </p>
        </div>
      )}

      {/* 1 — what is wrong, when anything is */}
      <AlertsCard alerts={data.alerts} />

      {/* 2 — what is mine, and what is coming */}
      {(data.assigned || data.upcoming) && (
        <div className="flex flex-wrap gap-3.5">
          {data.assigned && <AssignedToMe assigned={data.assigned} />}
          {data.upcoming && (
            <UpcomingWeek upcoming={data.upcoming} todayKey={todayKey} />
          )}
        </div>
      )}

      {/* 3 — is the machine working */}
      {data.tiles.length > 0 && (
        <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
          {data.tiles.map((tile) => (
            <StatTile
              key={tile.key}
              label={tile.label}
              value={tileValue(tile)}
              deltaValue={tile.delta ?? undefined}
              deltaSuffix={tile.delta_unit ? ` ${tile.delta_unit}` : ''}
              deltaLabel={tile.sub}
              chart={tile.spark?.length ? <TickBars values={tile.spark} /> : undefined}
            />
          ))}
        </div>
      )}

      {/* 4 — the two lists */}
      {(data.recent_campaigns || data.recent_submissions) && (
        <div className="flex flex-wrap gap-3.5">
          {data.recent_campaigns && (
            <section className="min-w-0 flex-1 basis-[340px] rounded-lg border bg-card shadow-card">
              <div className="flex items-center gap-2 border-b px-4 py-3">
                <h2 className="text-sm font-semibold">Recent campaigns</h2>
                <Link
                  to="/campaigns"
                  className="ml-auto inline-flex items-center gap-1 text-sm font-medium underline"
                >
                  All campaigns <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              {data.recent_campaigns.length === 0 ? (
                <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                  No campaigns yet.
                </p>
              ) : (
                data.recent_campaigns.map((campaign) => (
                  <Link
                    key={campaign.id}
                    to={`/campaigns/${campaign.id}`}
                    className="flex items-center gap-3 border-b px-4 py-2.5 last:border-b-0 hover:bg-accent"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">
                        {campaign.name}
                      </span>
                      <span className="block text-xs text-muted-foreground">
                        {campaign.sent_at
                          ? `Sent ${relative(campaign.sent_at)}`
                          : `Created ${relative(campaign.created_at)}`}
                      </span>
                    </span>
                    <span className="shrink-0 rounded-full border px-2 py-0.5 text-[10.5px] font-semibold capitalize text-muted-foreground">
                      {campaign.status}
                    </span>
                  </Link>
                ))
              )}
            </section>
          )}

          {data.recent_submissions && (
            <section className="min-w-0 flex-1 basis-[340px] rounded-lg border bg-card shadow-card">
              <div className="flex items-center gap-2 border-b px-4 py-3">
                <h2 className="text-sm font-semibold">Latest submissions</h2>
                <Link
                  to="/forms"
                  className="ml-auto inline-flex items-center gap-1 text-sm font-medium underline"
                >
                  All forms <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              {data.recent_submissions.length === 0 ? (
                <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                  No submissions yet.
                </p>
              ) : (
                data.recent_submissions.map((submission) => (
                  <div
                    key={submission.id}
                    className="flex items-center gap-3 border-b px-4 py-2.5 last:border-b-0"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">
                        {submission.contact_email ?? 'Anonymous'}
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {submission.form_name}
                      </span>
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {relative(submission.created_at)}
                    </span>
                  </div>
                ))
              )}
            </section>
          )}
        </div>
      )}

      {data.tiles.length > 0 && (
        <p className="text-[13px] text-muted-foreground">
          Trends, breakdowns and exports live in{' '}
          <Link to="/analytics" className="underline">
            Analytics
          </Link>
          . This screen keeps what asks for a decision today.
        </p>
      )}
    </div>
  );
}
