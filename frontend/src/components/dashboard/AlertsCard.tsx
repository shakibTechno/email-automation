import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import type { DashboardAlert } from '@/types/dashboard';

interface AlertsCardProps {
  alerts: DashboardAlert[];
}

/**
 * What is wrong right now, or nothing at all.
 *
 * Returns null on an empty list by design: a card that is always on screen is
 * one people stop reading, and then it cannot warn them. Severity is carried
 * by the word and the fill, never by colour alone.
 */
export function AlertsCard({ alerts }: AlertsCardProps) {
  if (alerts.length === 0) return null;

  return (
    <section className="rounded-lg border border-foreground/40 bg-card shadow-card">
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Needs attention</h2>
        <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-foreground px-1.5 text-[11px] font-semibold text-background">
          {alerts.length}
        </span>
      </div>

      {alerts.map((alert) => (
        <div
          key={alert.id}
          className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b px-4 py-3 last:border-b-0"
        >
          <span
            className={cn(
              'min-w-[58px] shrink-0 rounded border px-1.5 py-0.5 text-center text-[10px] font-semibold uppercase tracking-wider',
              alert.level === 'action'
                ? 'border-foreground bg-foreground text-background'
                : 'border-muted-foreground/50 text-foreground'
            )}
          >
            {alert.level === 'action' ? 'Action' : 'Soon'}
          </span>
          <span className="shrink-0 text-sm font-semibold">{alert.title}</span>
          <span className="min-w-0 flex-1 text-sm text-muted-foreground">
            {alert.detail}
          </span>
          <Link to={alert.url} className="shrink-0 text-sm font-medium underline">
            {alert.action}
          </Link>
        </div>
      ))}
    </section>
  );
}
