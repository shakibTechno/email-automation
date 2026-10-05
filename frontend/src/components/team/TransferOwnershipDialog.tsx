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
import { useTransferOwnership } from '@/hooks/useTeam';
import type { TeamMember } from '@/types/team';

interface TransferOwnershipDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  members: TeamMember[];
  currentUserId: string;
}

export function TransferOwnershipDialog({
  open,
  onOpenChange,
  members,
  currentUserId,
}: TransferOwnershipDialogProps) {
  const [selectedId, setSelectedId] = useState('');
  const transferOwnership = useTransferOwnership();

  const eligibleMembers = members.filter((m) => m.id !== currentUserId && m.role !== 'owner');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId) return;
    transferOwnership.mutate(selectedId, {
      onSuccess: () => {
        setSelectedId('');
        onOpenChange(false);
        // Reload page to reflect new role
        window.location.reload();
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Transfer Ownership</DialogTitle>
            <DialogDescription>
              Transfer organization ownership to another team member. You will be demoted to Admin.
              This action cannot be undone by you.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="new-owner">New owner</Label>
            <Select value={selectedId} onValueChange={setSelectedId}>
              <SelectTrigger className="mt-2">
                <SelectValue placeholder="Select a member" />
              </SelectTrigger>
              <SelectContent>
                {eligibleMembers.map((member) => (
                  <SelectItem key={member.id} value={member.id}>
                    {member.full_name || member.email} ({member.role})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="destructive"
              disabled={transferOwnership.isPending || !selectedId}
            >
              {transferOwnership.isPending ? 'Transferring...' : 'Transfer Ownership'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
