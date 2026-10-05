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
          ? 'bg-success/[.14] text-success hover:bg-success/[.14]'
          : ''
      }
    >
      {config.label}
    </Badge>
  );
};
