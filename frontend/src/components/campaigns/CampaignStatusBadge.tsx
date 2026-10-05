import { Badge } from '@/components/ui/badge';
import { CampaignStatus } from '@/types/campaign';
import { cn } from '@/lib/utils';

const statusConfig: Record<CampaignStatus, { label: string; className: string }> = {
  draft: { label: 'Draft', className: 'bg-gray-100 text-gray-800 border-gray-200' },
  scheduled: { label: 'Scheduled', className: 'bg-blue-100 text-blue-800 border-blue-200' },
  sending: { label: 'Sending', className: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  sent: { label: 'Sent', className: 'bg-green-100 text-green-800 border-green-200' },
  paused: { label: 'Paused', className: 'bg-orange-100 text-orange-800 border-orange-200' },
  cancelled: { label: 'Cancelled', className: 'bg-red-100 text-red-800 border-red-200' },
  archived: { label: 'Archived', className: 'bg-slate-100 text-slate-500 border-slate-200' },
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
