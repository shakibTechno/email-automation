import { Badge } from '@/components/ui/badge';
import { CampaignStatus } from '@/types/campaign';
import { cn } from '@/lib/utils';

const statusConfig: Record<CampaignStatus, { label: string; className: string }> = {
  draft: { label: 'Draft', className: 'bg-secondary text-muted-foreground border-border' },
  scheduled: { label: 'Scheduled', className: 'bg-info/[.14] text-info border-info/[.30]' },
  sending: { label: 'Sending', className: 'bg-warning/[.14] text-warning border-warning/[.30]' },
  sent: { label: 'Sent', className: 'bg-success/[.14] text-success border-success/[.30]' },
  paused: { label: 'Paused', className: 'bg-warning/[.14] text-warning border-warning/[.30]' },
  cancelled: { label: 'Cancelled', className: 'bg-destructive/[.14] text-destructive border-destructive/[.30]' },
  archived: { label: 'Archived', className: 'bg-secondary text-muted-foreground border-border' },
};

interface CampaignStatusBadgeProps {
  status: CampaignStatus;
  className?: string;
}

export const CampaignStatusBadge = ({ status, className }: CampaignStatusBadgeProps) => {
  const config = statusConfig[status] || statusConfig.draft;
  return (
    <Badge variant="outline" className={cn(config.className, className)}>
      {config.label}
    </Badge>
  );
};
