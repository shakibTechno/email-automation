import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useTeamMembers } from '@/hooks/useTeam';

interface MemberSelectProps {
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function MemberSelect({
  value,
  onChange,
  placeholder = 'Unassigned',
  disabled,
}: MemberSelectProps) {
  const { data: members = [] } = useTeamMembers();

  return (
    <Select
      value={value ?? 'unassigned'}
      onValueChange={(v) => onChange(v === 'unassigned' ? null : v)}
      disabled={disabled}
    >
      <SelectTrigger>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="unassigned">Unassigned</SelectItem>
        {(members as any[]).filter((m) => m.id).map((m) => (
          <SelectItem key={m.id} value={m.id}>
            {m.full_name || m.email}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
