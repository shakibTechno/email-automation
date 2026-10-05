import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import type { LeadSyncLog, SyncLogStatus } from '@/types/integration';

interface SyncHistoryTableProps {
  logs: LeadSyncLog[];
}

const STATUS_CONFIG: Record<SyncLogStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; className: string }> = {
  running: {
    label: 'Running',
    variant: 'default',
    className: 'bg-info/[.14] text-info hover:bg-info/[.14]',
  },
  completed: {
    label: 'Completed',
    variant: 'default',
    className: 'bg-success/[.14] text-success hover:bg-success/[.14]',
  },
  partial: {
    label: 'Partial',
    variant: 'default',
    className: 'bg-warning/[.14] text-warning hover:bg-warning/[.14]',
  },
  failed: {
    label: 'Failed',
    variant: 'destructive',
    className: '',
  },
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(seconds: number | null, status: SyncLogStatus): string {
  if (status === 'running') return 'In progress';
  if (seconds === null) return '-';
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

export function SyncHistoryTable({ logs }: SyncHistoryTableProps) {
  if (logs.length === 0) {
    return (
      <div className="text-center py-6 text-sm text-muted-foreground">
        No sync history yet.
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Found</TableHead>
          <TableHead className="text-right">Created</TableHead>
          <TableHead className="text-right">Updated</TableHead>
          <TableHead className="text-right">Failed</TableHead>
          <TableHead>Started</TableHead>
          <TableHead>Duration</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {logs.map((log) => {
          const statusConfig = STATUS_CONFIG[log.status];
          return (
            <TableRow key={log.id}>
              <TableCell>
                <Badge variant={statusConfig.variant} className={statusConfig.className}>
                  {statusConfig.label}
                </Badge>
              </TableCell>
              <TableCell className="text-right">{log.leads_found}</TableCell>
              <TableCell className="text-right">{log.leads_created}</TableCell>
              <TableCell className="text-right">{log.leads_updated}</TableCell>
              <TableCell className="text-right">
                {log.leads_failed > 0 ? (
                  <span className="text-destructive font-medium">{log.leads_failed}</span>
                ) : (
                  log.leads_failed
                )}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(log.started_at)}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDuration(log.duration_seconds, log.status)}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
