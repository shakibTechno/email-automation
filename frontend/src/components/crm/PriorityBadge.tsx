import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { DealPriority } from '@/types/crm';

const priorityConfig: Record<DealPriority, { label: string; className: string; dotColor: string }> = {
  low: { label: 'Low', className: 'bg-secondary/50 text-foreground border-border', dotColor: 'bg-muted-foreground' },
  medium: { label: 'Medium', className: 'bg-warning/[.10] text-warning border-warning/[.30]', dotColor: 'bg-warning' },
  high: { label: 'High', className: 'bg-destructive/[.10] text-destructive border-destructive/[.30]', dotColor: 'bg-destructive' },
};

interface PriorityBadgeProps {
  priority: DealPriority;
  className?: string;
  dotOnly?: boolean;
}

export const PriorityBadge = ({ priority, className, dotOnly }: PriorityBadgeProps) => {
  const config = priorityConfig[priority] || priorityConfig.medium;

  if (dotOnly) {
    return (
      <span
        className={cn('inline-block h-2 w-2 rounded-full', config.dotColor, className)}
        title={config.label}
      />
    );
  }

  return (
    <Badge variant="outline" className={cn(config.className, className)}>
      <span className={cn('mr-1.5 h-1.5 w-1.5 rounded-full inline-block', config.dotColor)} />
      {config.label}
    </Badge>
  );
};
