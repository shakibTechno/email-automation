import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, CheckCircle2, Clock, XCircle } from 'lucide-react';

import { StatTile } from '@/components/dashboard/StatTile';
import { SuspensionDialog, type SuspensionAction } from '@/components/landlord/SuspensionDialog';
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
import { useTenant } from '@/hooks/useLandlord';
import { formatDate, formatDateTime } from '@/lib/utils';
import { cn } from '@/lib/utils';

const full = (n: number) => new Intl.NumberFormat('en').format(n ?? 0);
const money = (n: number) =>
  new Intl.NumberFormat('en', { style: 'currency', currency: 'USD' }).format(n ?? 0);

const Section = ({
  title,
  aside,
  children,
}: {
  title: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
}) => (
  <div className="overflow-hidden rounded-lg border bg-card shadow-card">
    <div className="flex items-center gap-2 border-b p-3">
      <h2 className="text-[13.5px] font-semibold">{title}</h2>
      {aside && <div className="ml-auto">{aside}</div>}
    </div>
    {children}
  </div>
);

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div>
    <p className="stat-label">{label}</p>
    <p className="mt-0.5 text-[13px]">{children}</p>
  </div>
);

export const TenantDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const { data: tenant, isLoading, error } = useTenant(id);
  const [action, setAction] = useState<SuspensionAction | null>(null);

  if (isLoading) {
    return (
      <div className="w-full space-y-3.5">
        <Skeleton className="h-9 w-72 rounded-md" />
        <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[108px] w-full rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (error || !tenant) {
    return (
      <div className="w-full space-y-3.5">
        <Button variant="ghost" size="sm" asChild className="h-8 -ml-2">
          <Link to="/landlord/tenants">
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
            Tenants
          </Link>
        </Button>
        <div className="rounded-lg border bg-card px-4 py-14 text-center shadow-card">
          <h3 className="text-[14px] font-semibold">Tenant not found</h3>
          <p className="text-[12.5px] text-muted-foreground">
            It may have been deleted, or the link is wrong.
          </p>
        </div>
      </div>
    );
  }

  const d = tenant.deliverability;
  const overBounce =
    tenant.thresholds.bounce_pct !== null && d.bounce_rate > tenant.thresholds.bounce_pct;
  const overComplaint =
    tenant.thresholds.complaint_pct !== null && d.complaint_rate > tenant.thresholds.complaint_pct;
  const quotaPct =
    tenant.emails_limit > 0 ? Math.round((tenant.emails_used / tenant.emails_limit) * 100) : null;

  return (
    <div className="w-full space-y-3.5">
      <Button variant="ghost" size="sm" asChild className="-ml-2 h-8">
        <Link to="/landlord/tenants">
          <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
          Tenants
        </Link>
      </Button>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{tenant.name}</h1>
          <p className="text-[13px] text-muted-foreground">
            <span className="font-mono">{tenant.slug}</span>
            {' · '}
            {tenant.email || 'no billing email'}
            {' · joined '}
            {formatDate(tenant.created_at)}
          </p>
        </div>

        {/* Suspend sending is the reversible, proportionate response and sits
            first; suspending the whole account locks the customer out. */}
        <div className="flex flex-wrap items-center gap-1.5">
          {tenant.sending_paused ? (
            <Button variant="outline" size="sm" onClick={() => setAction('resume_sending')}>
              Resume sending
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setAction('suspend_sending')}>
              Suspend sending
            </Button>
          )}
          {tenant.is_active ? (
            <Button variant="destructive" size="sm" onClick={() => setAction('suspend_account')}>
              Suspend account
            </Button>
          ) : (
            <Button size="sm" onClick={() => setAction('restore_account')}>
              Restore account
            </Button>
          )}
        </div>
      </div>

      {!tenant.is_active && (
        <div className="flex items-start gap-2.5 rounded-lg border border-destructive/40 bg-destructive/[.07] p-3.5">
          <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <div className="text-[13px]">
            <p className="font-semibold">
              Account suspended{tenant.suspended_at ? ` ${formatDateTime(tenant.suspended_at)}` : ''}
            </p>
            <p className="text-muted-foreground">
              {tenant.suspension_reason || 'No reason recorded.'}
            </p>
          </div>
        </div>
      )}

      {tenant.is_active && tenant.sending_paused && (
        <div className="flex items-start gap-2.5 rounded-lg border border-warning/40 bg-warning/[.08] p-3.5">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <div className="text-[13px]">
            <p className="font-semibold">Sending paused</p>
            <p className="text-muted-foreground">
              {tenant.sending_pause_reason ||
                'Paused automatically by the bounce or complaint guardrails.'}
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Plan"
          value={tenant.plan.charAt(0).toUpperCase() + tenant.plan.slice(1)}
          deltaLabel={
            tenant.billing
              ? `${tenant.billing.status} · ${money(tenant.billing.price)}/${tenant.billing.interval === 'yearly' ? 'yr' : 'mo'}`
              : 'no subscription record'
          }
        />
        <StatTile
          label="Emails this period"
          value={full(tenant.emails_used)}
          deltaLabel={
            quotaPct === null
              ? 'unlimited'
              : `${quotaPct}% of ${full(tenant.emails_limit)}`
          }
          className={cn(quotaPct !== null && quotaPct >= 100 && 'border-destructive/50')}
        />
        <StatTile
          label="Bounce rate (30d)"
          value={`${d.bounce_rate}%`}
          deltaLabel={
            tenant.thresholds.bounce_pct === null
              ? `${full(d.bounced)} of ${full(d.sent)}`
              : `threshold ${tenant.thresholds.bounce_pct}%`
          }
          className={cn(overBounce && 'border-destructive/50')}
        />
        <StatTile
          label="Complaint rate (30d)"
          value={`${d.complaint_rate}%`}
          deltaLabel={
            tenant.thresholds.complaint_pct === null
              ? `${full(d.complained)} of ${full(d.sent)}`
              : `threshold ${tenant.thresholds.complaint_pct}%`
          }
          className={cn(overComplaint && 'border-destructive/50')}
        />
      </div>

      <div className="grid gap-3.5 lg:grid-cols-2">
        <Section title="Account">
          <div className="grid grid-cols-2 gap-3.5 p-3.5">
            <Field label="Users">{tenant.users}</Field>
            <Field label="Contacts">{full(tenant.contacts)}</Field>
            <Field label="From identity">
              {tenant.from_identity
                ? `${tenant.from_identity.name} <${tenant.from_identity.email}>`
                : <span className="text-muted-foreground">not configured</span>}
            </Field>
            <Field label="Subscription">
              {tenant.subscription_status ?? <span className="text-muted-foreground">none</span>}
            </Field>
            {tenant.billing?.trial_end && (
              <Field label="Trial ends">{formatDate(tenant.billing.trial_end)}</Field>
            )}
            {tenant.billing?.current_period_end && (
              <Field label="Period ends">{formatDate(tenant.billing.current_period_end)}</Field>
            )}
          </div>
        </Section>

        <Section
          title="Mail server"
          aside={
            tenant.mail_server?.last_synced_at && (
              <span className="flex items-center gap-1 font-mono text-[11px] text-subtle-foreground">
                <Clock className="h-3 w-3" />
                synced {formatDateTime(tenant.mail_server.last_synced_at)}
              </span>
            )
          }
        >
          {!tenant.mail_server ? (
            <div className="px-4 py-10 text-center text-[12.5px] text-muted-foreground">
              No mail server tenant provisioned yet. One is created the first time this
              organization sends.
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3.5 p-3.5">
              <Field label="External ID">
                <span className="font-mono text-[12px]">{tenant.mail_server.external_id}</span>
              </Field>
              <Field label="Status">
                <span
                  className={cn(
                    'font-medium',
                    tenant.mail_server.status === 'active' ? 'text-success' : 'text-destructive'
                  )}
                >
                  {tenant.mail_server.status}
                </span>
                {tenant.mail_server.suspension_reason && (
                  <span className="block text-[11.5px] text-muted-foreground">
                    {tenant.mail_server.suspension_reason}
                  </span>
                )}
              </Field>
              <Field label="Sent last hour">
                {full(tenant.mail_server.sent_last_hour)}
                {tenant.mail_server.send_limit_per_hour !== null && (
                  <span className="text-subtle-foreground">
                    {' / '}
                    {full(tenant.mail_server.send_limit_per_hour)}
                  </span>
                )}
              </Field>
              {/* Postal holds mail when a limit is hit or an address is
                  suppressed, and it does not move again on its own. */}
              <Field label="Queued / held">
                {full(tenant.queued)}
                {' / '}
                <span className={cn(tenant.held > 0 && 'font-semibold text-warning')}>
                  {full(tenant.held)}
                </span>
              </Field>
            </div>
          )}
        </Section>
      </div>

      <Section title="Sending domains">
        {tenant.domains.length === 0 ? (
          <div className="px-4 py-10 text-center text-[12.5px] text-muted-foreground">
            No sending domains added. This tenant sends from the platform default.
          </div>
        ) : (
          <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-full">Domain</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Sending</TableHead>
                  <TableHead className="text-right">Verified</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenant.domains.map((domain) => (
                  <TableRow key={domain.domain}>
                    <TableCell className="font-mono text-[12.5px]">{domain.domain}</TableCell>
                    <TableCell className="whitespace-nowrap">
                      {domain.status === 'verified' ? (
                        <span className="flex items-center gap-1 text-[12.5px] text-success">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          verified
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[12.5px] text-warning">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          {domain.status}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-[12.5px]">
                      {domain.sending_enabled ? 'enabled' : 'disabled'}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right text-[12.5px]">
                      {domain.verified_at ? (
                        formatDate(domain.verified_at)
                      ) : (
                        <span className="text-subtle-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Section>

      <Section title="Members">
        {tenant.members.length === 0 ? (
          <div className="px-4 py-10 text-center text-[12.5px] text-muted-foreground">
            This organization has no users — it was created without an owner.
          </div>
        ) : (
          <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-full">User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead className="text-right">Last seen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenant.members.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>
                      <span className="text-[13px] font-medium">{m.full_name || m.email}</span>
                      {m.full_name && (
                        <span className="ml-2 text-[11.5px] text-subtle-foreground">
                          {m.email}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-[11.5px]">
                      {m.role}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-[12.5px]">
                      {m.is_active ? (
                        'active'
                      ) : (
                        <span className="text-destructive">disabled</span>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right text-[12.5px]">
                      {m.last_login ? (
                        formatDateTime(m.last_login)
                      ) : (
                        <span className="text-subtle-foreground">never</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Section>

      <Section title="Recent campaigns">
        {tenant.recent_campaigns.length === 0 ? (
          <div className="px-4 py-10 text-center text-[12.5px] text-muted-foreground">
            This tenant has not created a campaign yet.
          </div>
        ) : (
          <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-full">Campaign</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Recipients</TableHead>
                  <TableHead className="text-right">Sent</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenant.recent_campaigns.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="text-[13px] font-medium">{c.name}</TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-[11.5px]">
                      {c.status}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums">
                      {full(c.recipient_count)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right text-[12.5px]">
                      {c.sent_at ? (
                        formatDate(c.sent_at)
                      ) : (
                        <span className="text-subtle-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Section>

      {action && (
        <SuspensionDialog
          open
          onOpenChange={(open) => !open && setAction(null)}
          action={action}
          tenantId={tenant.id}
          tenantName={tenant.name}
          sendingPaused={tenant.sending_paused}
        />
      )}
    </div>
  );
};
