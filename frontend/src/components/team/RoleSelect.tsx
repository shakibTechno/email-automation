import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { usePermissionCatalog, useRoles } from '@/hooks/useTeam';

// Copy for the built-ins. The catalog says what they grant; this says what
// they are for, which is what someone picking a role actually wants to read.
const PRESET_SUMMARY: Record<string, string> = {
  admin: 'Full access, manages the team',
  member: 'Creates and edits content',
  viewer: 'Read-only access',
};

interface RoleSelectProps {
  value: string;
  onChange: (role: string) => void;
  id?: string;
}

/**
 * Picks any role the organization can assign: the three assignable built-ins
 * plus its own.
 *
 * Both lists come from the API. A hardcoded dropdown was what made custom
 * roles unassignable from the UI even once the backend accepted them.
 */
export function RoleSelect({ value, onChange, id }: RoleSelectProps) {
  const { data: catalog } = usePermissionCatalog();
  const { data: customRoles } = useRoles();

  const presets = (catalog?.presets ?? []).filter((preset) => preset.assignable);
  const custom = customRoles ?? [];

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          <SelectLabel>Built-in</SelectLabel>
          {presets.map((preset) => (
            <SelectItem key={preset.slug} value={preset.slug}>
              {preset.name}
              {PRESET_SUMMARY[preset.slug] ? ` — ${PRESET_SUMMARY[preset.slug]}` : ''}
            </SelectItem>
          ))}
        </SelectGroup>
        {custom.length > 0 && (
          <SelectGroup>
            <SelectLabel>Your roles</SelectLabel>
            {custom.map((role) => (
              <SelectItem key={role.slug} value={role.slug}>
                {role.name} — {role.permissions.length} permission
                {role.permissions.length === 1 ? '' : 's'}
              </SelectItem>
            ))}
          </SelectGroup>
        )}
      </SelectContent>
    </Select>
  );
}
