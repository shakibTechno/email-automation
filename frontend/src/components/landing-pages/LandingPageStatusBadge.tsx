import { Badge } from '@/components/ui/badge';
import type { LandingPageStatus } from '@/types/landing-page';

interface LandingPageStatusBadgeProps {
  status: LandingPageStatus;
}

const statusConfig: Record<
  LandingPageStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  draft: { label: 'Draft', variant: 'secondary' },
  published: { label: 'Published', variant: 'default' },
};

export const LandingPageStatusBadge = ({ status }: LandingPageStatusBadgeProps) => {
  const config = statusConfig[status] || { label: status, variant: 'secondary' };

  return (
    <Badge
      variant={config.variant}
      className={
        status === 'published'
          ? 'bg-green-100 text-green-800 hover:bg-green-100'
          : ''
      }
    >
      {config.label}
    </Badge>
  );
};
