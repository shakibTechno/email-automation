import { cn } from '@/lib/utils';

interface UsageBarProps {
  label: string;
  current: number;
  limit: number;
  unit?: string;
  className?: string;
}

function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
  return num.toLocaleString();
}

export function UsageBar({ label, current, limit, unit = '', className }: UsageBarProps) {
  const percent = limit > 0 ? Math.min(100, Math.round((current / limit) * 100)) : 0;
  const isNearLimit = percent >= 80;
  const isAtLimit = percent >= 100;

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className={cn(
          'text-muted-foreground',
          isAtLimit && 'text-destructive font-medium',
          isNearLimit && !isAtLimit && 'text-warning font-medium',
        )}>
          {formatNumber(current)}{unit} / {limit === 0 ? 'Unlimited' : `${formatNumber(limit)}${unit}`}
        </span>
      </div>
      <div className="h-2 rounded-full bg-secondary overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-300',
            isAtLimit ? 'bg-destructive' : isNearLimit ? 'bg-warning' : 'bg-primary',
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
      {isAtLimit && (
        <p className="text-xs text-destructive">
          You&apos;ve reached your plan limit. Upgrade to continue.
        </p>
      )}
    </div>
  );
}
