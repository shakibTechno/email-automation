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
import { RoleSelect } from '@/components/team/RoleSelect';
import { useChangeRole } from '@/hooks/useTeam';
import type { TeamMember } from '@/types/team';

interface ChangeRoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  member: TeamMember | null;
}

export function ChangeRoleDialog({ open, onOpenChange, member }: ChangeRoleDialogProps) {
  // 'owner' is not assignable, so an owner opens the dialog on 'admin'.
  const [role, setRole] = useState(
    !member?.role || member.role === 'owner' ? 'admin' : member.role
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
            <div className="mt-2">
              <RoleSelect id="new-role" value={role} onChange={setRole} />
            </div>
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
