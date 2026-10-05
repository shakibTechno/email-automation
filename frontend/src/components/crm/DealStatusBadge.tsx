import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { DealStatus } from '@/types/crm';

const statusConfig: Record<DealStatus, { label: string; className: string }> = {
  open: { label: 'Open', className: 'bg-info/[.10] text-brand border-info/[.30]' },
  won: { label: 'Won', className: 'bg-success/[.10] text-success border-success/[.30]' },
  lost: { label: 'Lost', className: 'bg-destructive/[.10] text-destructive border-destructive/[.30]' },
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
