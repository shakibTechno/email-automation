import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useChangeRole } from '@/hooks/useTeam';
import type { TeamMember } from '@/types/team';

interface ChangeRoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  member: TeamMember | null;
}

export function ChangeRoleDialog({ open, onOpenChange, member }: ChangeRoleDialogProps) {
  const [role, setRole] = useState<'admin' | 'member' | 'viewer'>(
    (member?.role === 'owner' ? 'admin' : member?.role) as 'admin' | 'member' | 'viewer' || 'member'
  );
  const changeRole = useChangeRole();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!member) return;
    changeRole.mutate(
      { memberId: member.id, data: { role } },
      { onSuccess: () => onOpenChange(false) }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Change Role</DialogTitle>
            <DialogDescription>
              Change the role for {member?.full_name || member?.email}.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="new-role">New role</Label>
            <Select value={role} onValueChange={(v) => setRole(v as typeof role)}>
              <SelectTrigger className="mt-2">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="member">Member</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={changeRole.isPending}>
              {changeRole.isPending ? 'Updating...' : 'Update Role'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
