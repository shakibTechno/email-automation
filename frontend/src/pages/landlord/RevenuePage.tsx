import { Link } from 'react-router-dom';

import { StatTile } from '@/components/dashboard/StatTile';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useRevenue } from '@/hooks/useLandlord';
import { formatDate } from '@/lib/utils';
import { cn } from '@/lib/utils';

const full = (n: number) => new Intl.NumberFormat('en').format(n ?? 0);
const money = (n: number) =>
  new Intl.NumberFormat('en', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n ?? 0);

const Section = ({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) => (
  <div className="overflow-hidden rounded-lg border bg-card shadow-card">
    <div className="border-b p-3">
      <h2 className="text-[13.5px] font-semibold">{title}</h2>
      <p className="text-[11.5px] text-muted-foreground">{subtitle}</p>
    </div>
    {children}
  </div>
);

const Empty = ({ children }: { children: React.ReactNode }) => (
  <div className="px-4 py-10 text-center text-[12.5px] text-muted-foreground">{children}</div>
);

export const RevenuePage = () => {
  const { data, isLoading } = useRevenue();

  if (isLoading || !data) {
    return (
      <div className="w-full space-y-3.5">
        <Skeleton className="h-9 w-64 rounded-md" />
        <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[108px] w-full rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  const topPlan = [...data.by_plan].sort((a, b) => b.mrr - a.mrr)[0];
  const maxPlanMrr = Math.max(1, ...data.by_plan.map((p) => p.mrr));

  return (
    <div className="w-full space-y-3.5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Revenue</h1>
        <p className="text-[13px] text-muted-foreground">
          Recurring revenue by tier, plus the accounts that need attention this week.
        </p>
      </div>

      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="MRR"
          value={money(data.mrr)}
          deltaLabel={
            topPlan ? `${topPlan.plan} contributes ${money(topPlan.mrr)}` : 'no paid plans yet'
          }
        />
        <StatTile
          label="Paying tenants"
          value={full(data.paying_tenants)}
          deltaLabel={
            data.paying_tenants > 0
              ? `${money(Math.round(data.mrr / data.paying_tenants))} average`
              : 'none yet'
          }
        />
        <StatTile
          label="Trials ending (7d)"
          value={data.trials_ending.length}
          deltaLabel={data.trials_ending.length ? 'convert or lose them' : 'none expiring'}
          className={cn(data.trials_ending.length > 0 && 'border-warning/50')}
        />
        <StatTile
          label="Payment problems"
          value={data.at_risk.length}
          deltaLabel={data.at_risk.length ? 'past due or unpaid' : 'all current'}
          className={cn(data.at_risk.length > 0 && 'border-destructive/50')}
        />
      </div>

      <Section title="By plan" subtitle="Active subscriptions, normalised to a monthly figure.">
        {data.by_plan.length === 0 ? (
          <Empty>No active subscriptions yet.</Empty>
        ) : (
          <div className="flex flex-col gap-2.5 p-3.5">
            {data.by_plan.map((p) => (
              <div key={p.plan} className="flex items-center gap-3">
                <span className="w-24 shrink-0 font-mono text-[11.5px] uppercase text-muted-foreground">
                  {p.plan}
                </span>
                {/* A bar rather than a pie: the question is which tier carries
                    the revenue, which is a comparison of lengths. */}
                <div className="h-5 min-w-0 flex-1 overflow-hidden rounded bg-muted">
                  <div
                    className="h-full rounded bg-brand-fill"
                    style={{ width: `${Math.max(2, (p.mrr / maxPlanMrr) * 100)}%` }}
                  />
                </div>
                <span className="w-14 shrink-0 text-right text-[12px] tabular-nums text-muted-foreground">
                  {full(p.count)} ×
                </span>
                <span className="w-20 shrink-0 text-right text-[13px] font-semibold tabular-nums">
                  {money(p.mrr)}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className="grid gap-3.5 lg:grid-cols-2">
        <Section title="Trials ending" subtitle="Within the next 7 days.">
          {data.trials_ending.length === 0 ? (
            <Empty>No trials end in the next week.</Empty>
          ) : (
            <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-full">Tenant</TableHead>
                    <TableHead className="text-right">Ends</TableHead>
                    <TableHead className="text-right">Days</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.trials_ending.map((t) => (
                    <TableRow key={t.organization_id}>
                      <TableCell>
                        <Link
                          to={`/landlord/tenants/${t.organization_id}`}
                          className="text-[13px] font-medium hover:text-brand"
                        >
                          {t.organization_name}
                        </Link>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-right text-[12.5px]">
                        {formatDate(t.trial_end)}
                      </TableCell>
                      <TableCell
                        className={cn(
                          'whitespace-nowrap text-right tabular-nums',
                          t.days_left <= 1 && 'font-semibold text-warning'
                        )}
                      >
                        {t.days_left}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Section>

        <Section title="Payment problems" subtitle="Past due, unpaid or incomplete.">
          {data.at_risk.length === 0 ? (
            <Empty>Every subscription is current.</Empty>
          ) : (
            <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-full">Tenant</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead className="text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.at_risk.map((t) => (
                    <TableRow key={t.organization_id}>
                      <TableCell>
                        <Link
                          to={`/landlord/tenants/${t.organization_id}`}
                          className="text-[13px] font-medium hover:text-brand"
                        >
                          {t.organization_name}
                        </Link>
                      </TableCell>
                      <TableCell className="whitespace-nowrap font-mono text-[11.5px] uppercase">
                        {t.plan}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-right">
                        <span className="rounded bg-destructive/[.14] px-1.5 py-0.5 text-[11px] font-medium text-destructive">
                          {t.status}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Section>
      </div>

      <Section
        title="Near or over quota"
        subtitle="Candidates for an upgrade conversation — or already blocked from sending."
      >
        {data.near_quota.length === 0 ? (
          <Empty>No tenant is close to its email limit.</Empty>
        ) : (
          <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-full">Tenant</TableHead>
                  <TableHead className="text-right">Used</TableHead>
                  <TableHead className="text-right">Limit</TableHead>
                  <TableHead className="text-right">Usage</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.near_quota.map((t) => (
                  <TableRow key={t.organization_id}>
                    <TableCell>
                      <Link
                        to={`/landlord/tenants/${t.organization_id}`}
                        className="text-[13px] font-medium hover:text-brand"
                      >
                        {t.organization_name}
                      </Link>
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums">
                      {full(t.used)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums text-muted-foreground">
                      {full(t.limit)}
                    </TableCell>
                    <TableCell
                      className={cn(
                        'whitespace-nowrap text-right tabular-nums',
                        t.percent >= 100 ? 'font-semibold text-destructive' : 'text-warning'
                      )}
                    >
                      {t.percent}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Section>
    </div>
  );
};
