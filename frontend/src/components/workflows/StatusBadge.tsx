import { cn } from '@/lib/utils';
import { WorkflowStatus, ExecutionStatus } from '@/types/workflow';

interface StatusBadgeProps {
  status: WorkflowStatus | ExecutionStatus;
  className?: string;
}

const statusStyles: Record<WorkflowStatus | ExecutionStatus, string> = {
  draft: 'bg-secondary text-muted-foreground',
  active: 'bg-success/[.14] text-success',
  paused: 'bg-warning/[.14] text-warning',
  archived: 'bg-secondary text-muted-foreground',
  waiting: 'bg-info/[.14] text-info',
  completed: 'bg-success/[.14] text-success',
  failed: 'bg-destructive/[.14] text-destructive',
  cancelled: 'bg-secondary text-muted-foreground',
};

const statusLabels: Record<WorkflowStatus | ExecutionStatus, string> = {
  draft: 'Draft',
  active: 'Active',
  paused: 'Paused',
  archived: 'Archived',
  waiting: 'Waiting',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        statusStyles[status],
        className
      )}
    >
      {statusLabels[status]}
    </span>
  );
}
