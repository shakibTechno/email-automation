import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { MoreHorizontal, Plus, Send, X, UserPlus } from 'lucide-react';
import { RoleBadge } from '@/components/team/RoleBadge';
import { InviteDialog } from '@/components/team/InviteDialog';
import { ChangeRoleDialog } from '@/components/team/ChangeRoleDialog';
import { RemoveMemberDialog } from '@/components/team/RemoveMemberDialog';
import { TransferOwnershipDialog } from '@/components/team/TransferOwnershipDialog';
import {
  useTeamMembers,
  useTeamInvitations,
  useResendInvitation,
  useCancelInvitation,
} from '@/hooks/useTeam';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuthStore } from '@/stores/authStore';
import type { TeamMember } from '@/types/team';

export function TeamTab() {
  const { data: members = [], isLoading: membersLoading } = useTeamMembers();
  const { data: invitations = [], isLoading: invitationsLoading } = useTeamInvitations();
  const { canManageTeam, canTransferOwnership } = usePermissions();
  const user = useAuthStore((s) => s.user);
  const resendInvitation = useResendInvitation();
  const cancelInvitation = useCancelInvitation();

  const [inviteOpen, setInviteOpen] = useState(false);
  const [changeRoleMember, setChangeRoleMember] = useState<TeamMember | null>(null);
  const [removeMember, setRemoveMember] = useState<TeamMember | null>(null);
  const [transferOpen, setTransferOpen] = useState(false);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="space-y-6">
      {/* Members */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Team Members</CardTitle>
            <CardDescription>{members.length} member{members.length !== 1 ? 's' : ''}</CardDescription>
          </div>
          <div className="flex gap-2">
            {canTransferOwnership && members.length > 1 && (
              <Button variant="outline" size="sm" onClick={() => setTransferOpen(true)}>
                Transfer Ownership
              </Button>
            )}
            {canManageTeam && (
              <Button size="sm" onClick={() => setInviteOpen(true)}>
                <Plus className="h-4 w-4 mr-1" />
                Invite Member
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {membersLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading members...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Last Login</TableHead>
                  {canManageTeam && <TableHead className="w-[50px]" />}
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((member) => (
                  <TableRow key={member.id}>
                    <TableCell className="font-medium">
                      {member.full_name}
                      {member.id === user?.id && (
                        <span className="text-xs text-muted-foreground ml-2">(you)</span>
                      )}
                    </TableCell>
                    <TableCell>{member.email}</TableCell>
                    <TableCell><RoleBadge role={member.role} /></TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(member.last_login)}
                    </TableCell>
                    {canManageTeam && (
                      <TableCell>
                        {member.id !== user?.id && member.role !== 'owner' && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => setChangeRoleMember(member)}>
                                Change Role
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={() => setRemoveMember(member)}
                                className="text-destructive"
                              >
                                Remove Member
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pending Invitations */}
      {canManageTeam && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" />
              Pending Invitations
            </CardTitle>
            <CardDescription>
              {invitations.length} pending invitation{invitations.length !== 1 ? 's' : ''}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {invitationsLoading ? (
              <div className="text-center py-4 text-muted-foreground">Loading...</div>
            ) : invitations.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">
                No pending invitations
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Invited By</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invitations.map((inv) => (
                    <TableRow key={inv.id}>
                      <TableCell className="font-medium">{inv.email}</TableCell>
                      <TableCell><RoleBadge role={inv.role} /></TableCell>
                      <TableCell className="text-muted-foreground">
                        {inv.invited_by_name || 'Unknown'}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(inv.expires_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => resendInvitation.mutate(inv.id)}
                            title="Resend"
                          >
                            <Send className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive"
                            onClick={() => cancelInvitation.mutate(inv.id)}
                            title="Cancel"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* Dialogs */}
      <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} />
      <ChangeRoleDialog
        open={!!changeRoleMember}
        onOpenChange={(open) => !open && setChangeRoleMember(null)}
        member={changeRoleMember}
      />
      <RemoveMemberDialog
        open={!!removeMember}
        onOpenChange={(open) => !open && setRemoveMember(null)}
        member={removeMember}
      />
      <TransferOwnershipDialog
        open={transferOpen}
        onOpenChange={setTransferOpen}
        members={members}
        currentUserId={user?.id || ''}
      />
    </div>
  );
}
