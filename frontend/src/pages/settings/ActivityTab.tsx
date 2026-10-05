import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { useActivityLog } from '@/hooks/useTeam';

const actionLabels: Record<string, string> = {
  member_invited: 'Member Invited',
  member_joined: 'Member Joined',
  member_removed: 'Member Removed',
  role_changed: 'Role Changed',
  invitation_cancelled: 'Invitation Cancelled',
  invitation_resent: 'Invitation Resent',
  ownership_transferred: 'Ownership Transferred',
  org_settings_updated: 'Settings Updated',
};

function formatDetails(action: string, details: Record<string, unknown>): string {
  switch (action) {
    case 'role_changed':
      return `${details.old_role} → ${details.new_role}`;
    case 'member_invited':
      return `as ${details.role}`;
    case 'member_joined':
      return `as ${details.role}`;
    case 'org_settings_updated':
      return Array.isArray(details.fields) ? details.fields.join(', ') : '';
    default:
      return '';
  }
}

export function ActivityTab() {
  const { data: logs = [], isLoading } = useActivityLog();

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity Log</CardTitle>
        <CardDescription>Recent team management activity in your organization.</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="text-center py-8 text-muted-foreground">Loading activity...</div>
        ) : logs.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">No activity recorded yet.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Action</TableHead>
                <TableHead>Performed By</TableHead>
                <TableHead>Target</TableHead>
                <TableHead>Details</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>
                    <Badge variant="outline">
                      {actionLabels[log.action] || log.action}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">
                    {log.user_name || 'System'}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {log.target_email || '-'}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {formatDetails(log.action, log.details)}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {formatDate(log.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
