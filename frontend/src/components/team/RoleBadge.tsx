import { Badge } from '@/components/ui/badge';
import type { UserRole } from '@/types/team';

const roleConfig: Record<UserRole, { label: string; variant: string; className: string }> = {
  owner: { label: 'Owner', variant: 'default', className: 'bg-purple-100 text-purple-800 hover:bg-purple-100' },
  admin: { label: 'Admin', variant: 'default', className: 'bg-blue-100 text-blue-800 hover:bg-blue-100' },
  member: { label: 'Member', variant: 'default', className: 'bg-green-100 text-green-800 hover:bg-green-100' },
  viewer: { label: 'Viewer', variant: 'default', className: 'bg-gray-100 text-gray-800 hover:bg-gray-100' },
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
