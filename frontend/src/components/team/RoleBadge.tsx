import { Badge } from '@/components/ui/badge';
import type { UserRole } from '@/types/team';

const builtInStyles: Record<string, string> = {
  owner: 'bg-info/[.14] text-info hover:bg-info/[.14]',
  admin: 'bg-info/[.14] text-info hover:bg-info/[.14]',
  member: 'bg-success/[.14] text-success hover:bg-success/[.14]',
  viewer: 'bg-secondary text-muted-foreground hover:bg-secondary',
};

const builtInLabels: Record<string, string> = {
  owner: 'Owner',
  admin: 'Admin',
  member: 'Member',
  viewer: 'Viewer',
};

// A role the organization defined. Its own colour, so it reads as something
// other than one of the four everyone has.
const CUSTOM = 'bg-primary/[.12] text-primary hover:bg-primary/[.12]';

interface RoleBadgeProps {
  role: UserRole;
  /** The server's label for the role. Required for custom roles, which have
   *  no label this component could know. */
  roleName?: string;
}

export function RoleBadge({ role, roleName }: RoleBadgeProps) {
  const isBuiltIn = role in builtInStyles;
  return (
    <Badge
      variant="outline"
      className={isBuiltIn ? builtInStyles[role] : CUSTOM}
    >
      {roleName || builtInLabels[role] || role}
    </Badge>
  );
}
