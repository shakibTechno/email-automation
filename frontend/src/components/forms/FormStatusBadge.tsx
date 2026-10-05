import { Badge } from '@/components/ui/badge';
import { FormStatus } from '@/types/form';
import { cn } from '@/lib/utils';

const statusConfig: Record<FormStatus, { label: string; className: string }> = {
  active: { label: 'Active', className: 'bg-green-100 text-green-800 border-green-200' },
  inactive: { label: 'Inactive', className: 'bg-gray-100 text-gray-800 border-gray-200' },
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
