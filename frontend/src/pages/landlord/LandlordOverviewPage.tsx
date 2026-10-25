import { useState } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

import { StatTile } from '@/components/dashboard/StatTile';
import { AreaSparkline, HeroAreaChart } from '@/components/dashboard/charts';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { usePlatformOverview, useDeliverability } from '@/hooks/useLandlord';
import { cn } from '@/lib/utils';

const RANGES = [7, 30, 90];

const full = (n: number) => new Intl.NumberFormat('en').format(n ?? 0);
const compact = (n: number) =>
  new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(n ?? 0);

export const LandlordOverviewPage = () => {
  const [days, setDays] = useState(30);
  const { data, isLoading } = usePlatformOverview(days);
  // The risk count is surfaced here rather than only on its own page: a tenant
  // damaging the shared IP is the one thing an operator should not have to go
  // looking for.
  const { data: risk } = useDeliverability();

  const signups = data?.signups_by_day.map((p) => p.count) ?? [];
  const signupLabels = data?.signups_by_day.map((p) => p.date) ?? [];

  return (
    <div className="w-full space-y-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Platform overview</h1>
          <p className="text-[13px] text-muted-foreground">
            Every tenant on the platform, in aggregate.
          </p>
        </div>
        <div className="flex items-center gap-1">
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setDays(r)}
              className={cn(
                'rounded-md border px-2.5 py-1 font-mono text-[11px] transition-colors',
                days === r
                  ? 'border-transparent bg-brand-fill text-brand-ink'
                  : 'border-border text-muted-foreground hover:text-foreground'
              )}
            >
              {r}d
            </button>
          ))}
        </div>
      </div>

      {risk && risk.at_risk > 0 && (
        <div className="flex items-start gap-2.5 rounded-lg border border-destructive/40 bg-destructive/[.07] p-3.5">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <div className="text-[13px]">
            <p className="font-semibold text-foreground">
              {risk.at_risk} {risk.at_risk === 1 ? 'tenant is' : 'tenants are'} over their
              bounce threshold
            </p>
            <p className="text-muted-foreground">
              All tenants share one sending IP, so this affects everyone's delivery.
            </p>
          </div>
          <Button variant="outline" size="sm" className="ml-auto h-8" asChild>
            <a href="/landlord/deliverability">Review</a>
          </Button>
        </div>
      )}

      {isLoading || !data ? (
        <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[108px] w-full rounded-lg" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
              label="Tenants"
              value={full(data.tenants.total)}
              deltaLabel={`${full(data.tenants.new_in_period)} new in ${days}d`}
              chart={<AreaSparkline values={signups} />}
            />
            <StatTile
              label="Active tenants"
              value={full(data.tenants.active)}
              deltaLabel={
                data.tenants.suspended
                  ? `${full(data.tenants.suspended)} suspended`
                  : 'none suspended'
              }
            />
            <StatTile
              label={`Recipients mailed (${days}d)`}
              value={compact(data.emails.sent)}
              deltaLabel={`${full(data.emails.delivered)} delivered`}
            />
            <StatTile
              label="Bounce rate"
              value={`${data.emails.bounce_rate}%`}
              deltaLabel={`${full(data.emails.bounced)} bounced`}
            />
          </div>

          <div className="grid gap-3.5 lg:grid-cols-3">
            <div className="rounded-lg border bg-card p-4 shadow-card lg:col-span-2">
              <p className="stat-label mb-2">Signups</p>
              <HeroAreaChart values={signups} labels={signupLabels} />
            </div>

            <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-1">
              <StatTile label="Customer users" value={full(data.users)} />
              <StatTile label="Contacts stored" value={compact(data.contacts)} />
              <StatTile label={`Campaigns sent (${days}d)`} value={full(data.campaigns_sent)} />
            </div>
          </div>

          <p className="flex items-center gap-1.5 font-mono text-[11px] text-subtle-foreground">
            <RefreshCw className="h-3 w-3" />
            Cached — generated {new Date(data.generated_at).toLocaleTimeString()}
          </p>
        </>
      )}
    </div>
  );
};
