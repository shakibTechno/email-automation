import { cn } from '@/lib/utils';

interface StatTileProps {
  label: string;
  value: string | number;
  /** Signed percentage. Direction colours the figure; omit when there is no comparison. */
  deltaValue?: number;
  deltaLabel?: string;
  /** A chart primitive from ./charts, or nothing for a bare figure. */
  chart?: React.ReactNode;
  className?: string;
}

/**
 * The repeating tile across the top of the dashboard: label, figure, a glance
 * of shape, then the comparison. Same edges and baselines on every one, so the
 * row reads as a single object rather than four cards.
 */
export const StatTile = ({
  label,
  value,
  deltaValue,
  deltaLabel,
  chart,
  className,
}: StatTileProps) => {
  const hasDelta = typeof deltaValue === 'number' && Number.isFinite(deltaValue);
  const up = hasDelta && deltaValue! >= 0;

  return (
    <div className={cn('rounded-lg border bg-card p-4 shadow-card', className)}>
      <div className="flex items-center gap-2">
        <span className="stat-label">{label}</span>
        <span className="ml-auto leading-none text-subtle-foreground">⋯</span>
      </div>

      <p className="stat-value">{value}</p>

      {chart ?? <div className="h-[44px]" />}

      <p className={cn('delta', hasDelta && (up ? 'delta-up' : 'delta-down'))}>
        {hasDelta && (
          <b className="font-semibold">
            {up ? '+' : ''}
            {deltaValue!.toFixed(1)}%
          </b>
        )}
        <span className={cn(hasDelta && 'text-subtle-foreground')}>{deltaLabel}</span>
      </p>
    </div>
  );
};
