import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { DealStatus } from '@/types/crm';

const statusConfig: Record<DealStatus, { label: string; className: string }> = {
  open: { label: 'Open', className: 'bg-blue-50 text-blue-700 border-blue-200' },
  won: { label: 'Won', className: 'bg-green-50 text-green-700 border-green-200' },
  lost: { label: 'Lost', className: 'bg-red-50 text-red-700 border-red-200' },
};

interface DealStatusBadgeProps {
  status: DealStatus;
  className?: string;
}

export const DealStatusBadge = ({ status, className }: DealStatusBadgeProps) => {
  const config = statusConfig[status] || statusConfig.open;
  return (
    <Badge variant="outline" className={cn(config.className, className)}>
      {config.label}
    </Badge>
  );
};
