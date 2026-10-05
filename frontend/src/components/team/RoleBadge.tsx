import { Badge } from '@/components/ui/badge';
import type { UserRole } from '@/types/team';

const roleConfig: Record<UserRole, { label: string; variant: string; className: string }> = {
  owner: { label: 'Owner', variant: 'default', className: 'bg-info/[.14] text-info hover:bg-info/[.14]' },
  admin: { label: 'Admin', variant: 'default', className: 'bg-info/[.14] text-info hover:bg-info/[.14]' },
  member: { label: 'Member', variant: 'default', className: 'bg-success/[.14] text-success hover:bg-success/[.14]' },
  viewer: { label: 'Viewer', variant: 'default', className: 'bg-secondary text-muted-foreground hover:bg-secondary' },
};

interface RoleBadgeProps {
  role: UserRole;
}

export function RoleBadge({ role }: RoleBadgeProps) {
  const config = roleConfig[role] || roleConfig.viewer;
  return (
    <Badge variant="outline" className={config.className}>
      {config.label}
    </Badge>
  );
}
