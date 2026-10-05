import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { DealPriority } from '@/types/crm';

const priorityConfig: Record<DealPriority, { label: string; className: string; dotColor: string }> = {
  low: { label: 'Low', className: 'bg-gray-50 text-gray-700 border-gray-200', dotColor: 'bg-gray-400' },
  medium: { label: 'Medium', className: 'bg-yellow-50 text-yellow-700 border-yellow-200', dotColor: 'bg-yellow-400' },
  high: { label: 'High', className: 'bg-red-50 text-red-700 border-red-200', dotColor: 'bg-red-400' },
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
