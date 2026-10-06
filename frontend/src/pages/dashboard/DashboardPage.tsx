import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { format, parseISO } from 'date-fns';
import {
  Users,
  Mail,
  FileText,
  Layout,
  Plus,
  ArrowRight,
  RefreshCw,
  Clock,
  Sparkles,
  Info,
} from 'lucide-react';

import { useDashboard } from '@/hooks/useDashboard';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { StatTile } from '@/components/dashboard/StatTile';
import {
  AreaSparkline,
  BarGroup,
  DottedSparkline,
  HeroAreaChart,
  TickBars,
} from '@/components/dashboard/charts';
import { cn } from '@/lib/utils';

const RANGES = [7, 30, 90] as const;

/**
 * Period-over-period change, comparing the back half of a series with the
 * front half. Returns undefined when there is not enough data to be honest
 * about a trend — a tile shows no delta rather than a fabricated one.
 */
const halfOverHalf = (values: number[]): number | undefined => {
  if (values.length < 4) return undefined;
  const mid = Math.floor(values.length / 2);
  const prev = values.slice(0, mid).reduce((a, b) => a + b, 0);
  const curr = values.slice(mid).reduce((a, b) => a + b, 0);
  if (prev === 0) return curr > 0 ? 100 : undefined;
  return ((curr - prev) / prev) * 100;
};

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'success' | 'warning' | 'info' | 'destructive'> = {
  sent: 'success',
  sending: 'info',
  scheduled: 'default',
  draft: 'warning',
  paused: 'warning',
  cancelled: 'destructive',
  archived: 'secondary',
};

const compact = (n: number) => new Intl.NumberFormat('en', { notation: 'compact' }).format(n);
const full = (n: number) => new Intl.NumberFormat('en').format(n);

const DashboardSkeleton = () => (
  <div className="flex flex-col gap-3.5">
    <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-[150px] rounded-lg" />
      ))}
    </div>
    <div className="grid gap-3.5 lg:grid-cols-3">
      <Skeleton className="h-[260px] rounded-lg lg:col-span-2" />
      <Skeleton className="h-[260px] rounded-lg" />
    </div>
  </div>
);

export const DashboardPage = () => {
  const navigate = useNavigate();
  const [days, setDays] = useState<number>(30);
  const { data, isLoading, isError, refetch } = useDashboard(days);

  if (isLoading) return <DashboardSkeleton />;

  if (isError || !data) {
    return (
      <div className="grid place-items-center rounded-lg border bg-card p-10 text-center shadow-card">
        <Info className="mb-3 h-5 w-5 text-destructive" />
        <h3 className="mb-1 text-[15px] font-semibold">Could not load your dashboard</h3>
        <p className="mb-4 text-[12.5px] text-muted-foreground">
          The API did not respond. Your data is safe — this is a read-only view.
        </p>
        <Button onClick={() => refetch()} size="sm">
          <RefreshCw className="h-3.5 w-3.5" /> Try again
        </Button>
      </div>
    );
  }

  const {
    overview,
    contact_growth,
    campaign_stats,
    form_stats,
    landing_page_stats,
    recent_campaigns,
    recent_submissions,
    top_landing_pages,
  } = data;

  const growth = contact_growth.map((d) => d.count);
  const submissions = form_stats.submissions_by_day.map((d) => d.count);
  const views = landing_page_stats.views_by_day.map((d) => d.views);

  // Labels thin out to six marks so they never collide at narrow widths.
  const axisLabels = (dates: string[]) => {
    if (dates.length === 0) return [];
    const step = Math.max(1, Math.ceil(dates.length / 6));
    return dates
      .filter((_, i) => i % step === 0)
      .map((d) => {
        try {
          return format(parseISO(d), 'd MMM');
        } catch {
          return d;
        }
      });
  };

  const deliveredRate = campaign_stats.emails_sent
    ? (campaign_stats.emails_delivered / campaign_stats.emails_sent) * 100
    : 0;

  const quickActions = [
    { label: 'New campaign', icon: Mail, to: '/campaigns/new' },
    { label: 'Add contact', icon: Users, to: '/contacts/new' },
    { label: 'Create form', icon: FileText, to: '/forms/new' },
    { label: 'Landing page', icon: Layout, to: '/landing-pages' },
  ];

  return (
    <div className="flex flex-col gap-3.5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
        <p className="text-[13px] text-muted-foreground">
          Audience growth, sending health and pipeline at a glance.
        </p>
      </div>

      {/* period + quick actions */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-md border bg-card p-0.5">
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
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

        <div className="flex-1" />

        {quickActions.map((a) => (
          <Button key={a.to} variant="outline" size="sm" onClick={() => navigate(a.to)}>
            <a.icon className="h-3.5 w-3.5" /> {a.label}
          </Button>
        ))}
      </div>

      {/* headline figures */}
      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Total contacts"
          value={full(overview.contacts.total)}
          deltaValue={halfOverHalf(growth)}
          deltaLabel={`last ${days} days`}
          chart={<DottedSparkline values={growth} />}
        />
        <StatTile
          label="Emails sent"
          value={compact(campaign_stats.emails_sent)}
          deltaValue={deliveredRate ? deliveredRate - 100 : undefined}
          deltaLabel={`${full(campaign_stats.emails_delivered)} delivered`}
        />
        <StatTile
          label="Open rate"
          value={`${campaign_stats.open_rate.toFixed(1)}%`}
          deltaLabel={`${full(campaign_stats.emails_opened)} opens · ${campaign_stats.click_rate.toFixed(1)}% clicked`}
          chart={<TickBars values={submissions.length ? submissions : views} />}
        />
        <StatTile
          label="Page views"
          value={compact(landing_page_stats.total_views)}
          deltaValue={halfOverHalf(views)}
          deltaLabel={`${full(landing_page_stats.unique_views)} unique`}
          chart={<AreaSparkline values={views} />}
        />
      </div>

      {/* hero + email performance */}
      <div className="grid gap-3.5 lg:grid-cols-3">
        <div className="chart-hero rounded-lg border p-4 shadow-card lg:col-span-2">
          <div className="mb-3 flex items-center gap-2">
            <h3 className="text-[16px] font-semibold tracking-tight">Contact growth</h3>
            <span className="ml-auto font-mono text-[11.5px] text-muted-foreground">
              {full(growth.reduce((a, b) => a + b, 0))} added in {days} days
            </span>
          </div>
          <HeroAreaChart values={growth} labels={axisLabels(contact_growth.map((d) => d.date))} />
        </div>

        <div className="rounded-lg border bg-card p-4 shadow-card">
          <div className="mb-3 flex items-center gap-2">
            <h3 className="text-[13.5px] font-semibold">Email performance</h3>
            <span className="ml-auto leading-none text-subtle-foreground">⋯</span>
          </div>
          <p className="stat-value text-[28px]">
            {campaign_stats.open_rate.toFixed(1)}
            <span className="text-[15px] text-subtle-foreground">% open</span>
          </p>

          <div className="mt-4 flex flex-col gap-2.5">
            {[
              ['Sent', campaign_stats.emails_sent],
              ['Delivered', campaign_stats.emails_delivered],
              ['Opened', campaign_stats.emails_opened],
              ['Clicked', campaign_stats.emails_clicked],
            ].map(([label, value]) => {
              const pct = campaign_stats.emails_sent
                ? ((value as number) / campaign_stats.emails_sent) * 100
                : 0;
              return (
                <div key={label as string}>
                  <div className="mb-1 flex justify-between text-[12px]">
                    <span className="text-muted-foreground">{label}</span>
                    <b className="font-mono text-[11.5px]">{full(value as number)}</b>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${Math.min(100, pct)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* three-up */}
      <div className="grid gap-3.5 lg:grid-cols-3">
        <div className="rounded-lg border bg-card p-4 shadow-card">
          <div className="mb-3 flex items-center gap-2">
            <h3 className="text-[13.5px] font-semibold">Form submissions</h3>
            <span className="ml-auto font-mono text-[11.5px] text-brand">
              {full(form_stats.total_submissions)}
            </span>
          </div>
          <BarGroup values={submissions} labels={axisLabels(form_stats.submissions_by_day.map((d) => d.date))} />
        </div>

        <div className="rounded-lg border bg-card p-4 shadow-card">
          <div className="mb-3 flex items-center gap-2">
            <h3 className="text-[13.5px] font-semibold">Landing page views</h3>
            <span className="ml-auto font-mono text-[11.5px] text-brand">
              {full(landing_page_stats.total_views)}
            </span>
          </div>
          <BarGroup values={views} labels={axisLabels(landing_page_stats.views_by_day.map((d) => d.date))} />
        </div>

        <div className="rounded-lg border bg-card p-4 shadow-card">
          <div className="mb-3 flex items-center gap-2">
            <h3 className="text-[13.5px] font-semibold">Top pages</h3>
            <span className="ml-auto leading-none text-subtle-foreground">⋯</span>
          </div>
          {top_landing_pages.length === 0 ? (
            <p className="py-6 text-center text-[12.5px] text-subtle-foreground">
              No published pages yet.
            </p>
          ) : (
            top_landing_pages.slice(0, 4).map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => navigate(`/landing-pages/${p.id}`)}
                className="flex w-full items-center gap-2.5 border-b py-2.5 text-left last:border-b-0 hover:opacity-80"
              >
                <span className="grid h-7 w-7 flex-none place-items-center rounded-md bg-secondary text-muted-foreground">
                  <Layout className="h-3.5 w-3.5" />
                </span>
                <span className="min-w-0 flex-1">
                  <b className="block truncate text-[12.5px] font-semibold">{p.name}</b>
                  <span className="block truncate font-mono text-[10.5px] text-subtle-foreground">
                    /p/{p.slug}
                  </span>
                </span>
                <span className="flex-none text-right">
                  <b className="block font-mono text-[12px]">{compact(p.view_count)}</b>
                  <span className="block font-mono text-[10px] text-brand">
                    {p.conversion_count} conv.
                  </span>
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      {/* recent activity */}
      <div className="grid gap-3.5 lg:grid-cols-3">
        <div className="rounded-lg border bg-card p-4 shadow-card lg:col-span-2">
          <div className="mb-3 flex items-center gap-2">
            <h3 className="text-[13.5px] font-semibold">Recent campaigns</h3>
            <Button variant="outline" size="sm" className="ml-auto" onClick={() => navigate('/campaigns')}>
              View all <ArrowRight className="h-3 w-3" />
            </Button>
          </div>

          {recent_campaigns.length === 0 ? (
            <div className="py-8 text-center">
              <p className="mb-3 text-[12.5px] text-subtle-foreground">No campaigns yet.</p>
              <Button size="sm" onClick={() => navigate('/campaigns/new')}>
                <Plus className="h-3.5 w-3.5" /> Create your first campaign
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Campaign</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Sent</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recent_campaigns.slice(0, 5).map((c) => (
                  <TableRow
                    key={c.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/campaigns/${c.id}`)}
                  >
                    <TableCell className="font-semibold text-foreground">{c.name}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[c.status] ?? 'secondary'}>{c.status}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-[12px]">
                      {c.sent_at ? format(parseISO(c.sent_at), 'd MMM') : '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        <div className="rounded-lg border bg-card p-4 shadow-card">
          <div className="mb-3 flex items-center gap-2">
            <h3 className="text-[13.5px] font-semibold">Latest submissions</h3>
            <span className="ml-auto leading-none text-subtle-foreground">⋯</span>
          </div>

          {recent_submissions.length === 0 ? (
            <div className="flex gap-2.5 rounded-md bg-brand/[.10] p-3 text-[12px] text-muted-foreground">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 flex-none text-brand" />
              <span>
                Publish a form to start capturing leads — submissions appear here as they arrive.
              </span>
            </div>
          ) : (
            recent_submissions.slice(0, 5).map((s) => (
              <div key={s.id} className="flex items-center gap-2.5 border-b py-2.5 last:border-b-0">
                <span className="grid h-7 w-7 flex-none place-items-center rounded-md bg-secondary text-muted-foreground">
                  <FileText className="h-3.5 w-3.5" />
                </span>
                <span className="min-w-0 flex-1">
                  <b className="block truncate text-[12.5px] font-semibold">
                    {s.contact_email ?? 'Anonymous'}
                  </b>
                  <span className="block truncate text-[11px] text-subtle-foreground">
                    {s.form_name}
                  </span>
                </span>
                <span className="flex flex-none items-center gap-1 font-mono text-[10.5px] text-subtle-foreground">
                  <Clock className="h-3 w-3" />
                  {format(parseISO(s.created_at), 'd MMM')}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
