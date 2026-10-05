import { Badge } from '@/components/ui/badge';
import { FormStatus } from '@/types/form';
import { cn } from '@/lib/utils';

const statusConfig: Record<FormStatus, { label: string; className: string }> = {
  active: { label: 'Active', className: 'bg-success/[.14] text-success border-success/[.30]' },
  inactive: { label: 'Inactive', className: 'bg-secondary text-muted-foreground border-border' },
};

interface FormStatusBadgeProps {
  status: FormStatus;
  className?: string;
}

export const FormStatusBadge = ({ status, className }: FormStatusBadgeProps) => {
  const config = statusConfig[status] || statusConfig.inactive;
  return (
    <Badge variant="outline" className={cn(config.className, className)}>
      {config.label}
    </Badge>
  );
};
