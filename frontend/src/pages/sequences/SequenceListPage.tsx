import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Plus,
  Search,
  MoreHorizontal,
  Mail,
  Play,
  Pause,
  Copy,
  Trash2,
  BarChart2,
} from 'lucide-react';
import { useSequences, useSequenceMutations } from '@/hooks/useSequences';
import type { EmailSequenceListItem } from '@/types/sequence';
import { formatDistanceToNow } from 'date-fns';

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-secondary text-muted-foreground',
  active: 'bg-success/[.14] text-success',
  paused: 'bg-warning/[.14] text-warning',
  archived: 'bg-secondary text-muted-foreground',
};

export default function SequenceListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const { data, isLoading } = useSequences(search ? { search } : undefined);
  const { remove, activate, pause, duplicate } = useSequenceMutations();

  const sequences: EmailSequenceListItem[] = data?.results || [];

  const handleDelete = (id: string) => {
    if (confirm('Delete this sequence? Enrolled contacts will not receive further emails.')) {
      remove.mutate(id);
    }
  };

  return (
    <div className="w-full space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Email Sequences</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Automate multi-step email series for contacts
          </p>
        </div>
        <Button onClick={() => navigate('/sequences/new')}>
          <Plus className="h-4 w-4 mr-2" />
          New Sequence
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-subtle-foreground" />
        <Input
          placeholder="Search sequences..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading...</div>
      ) : sequences.length === 0 ? (
        <div className="text-center py-16 border-2 border-dashed rounded-lg">
          <Mail className="h-12 w-12 mx-auto text-subtle-foreground mb-4" />
          <h3 className="text-lg font-medium text-foreground">No sequences yet</h3>
          <p className="text-sm text-muted-foreground mt-1 mb-4">
            Create a sequence to send automated email series to contacts.
          </p>
          <Button onClick={() => navigate('/sequences/new')}>
            <Plus className="h-4 w-4 mr-2" />
            Create Sequence
          </Button>
        </div>
      ) : (
        <div className="rounded-lg border bg-card shadow-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-center">Steps</TableHead>
                <TableHead className="text-center">Enrolled</TableHead>
                <TableHead className="text-center">Completed</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {sequences.map((seq) => (
                <TableRow
                  key={seq.id}
                  className="cursor-pointer hover:bg-secondary/50"
                  onClick={() => navigate(`/sequences/${seq.id}`)}
                >
                  <TableCell>
                    <div className="font-medium text-foreground">{seq.name}</div>
                    {seq.description && (
                      <div className="text-xs text-muted-foreground truncate max-w-xs">{seq.description}</div>
                    )}
                    {seq.sender_email && (
                      <div className="text-xs text-subtle-foreground">{seq.sender_name || seq.sender_email}</div>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[seq.status]}`}>
                      {seq.status.charAt(0).toUpperCase() + seq.status.slice(1)}
                    </span>
                  </TableCell>
                  <TableCell className="text-center">{seq.step_count}</TableCell>
                  <TableCell className="text-center">{seq.enrolled_count}</TableCell>
                  <TableCell className="text-center">{seq.completed_count}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDistanceToNow(new Date(seq.created_at), { addSuffix: true })}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => navigate(`/sequences/${seq.id}`)}>
                          <BarChart2 className="h-4 w-4 mr-2" />
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => navigate(`/sequences/${seq.id}/edit`)}>
                          Edit
                        </DropdownMenuItem>
                        {seq.status === 'draft' || seq.status === 'paused' ? (
                          <DropdownMenuItem onClick={() => activate.mutate(seq.id)}>
                            <Play className="h-4 w-4 mr-2" />
                            Activate
                          </DropdownMenuItem>
                        ) : seq.status === 'active' ? (
                          <DropdownMenuItem onClick={() => pause.mutate(seq.id)}>
                            <Pause className="h-4 w-4 mr-2" />
                            Pause
                          </DropdownMenuItem>
                        ) : null}
                        <DropdownMenuItem onClick={() => duplicate.mutate(seq.id)}>
                          <Copy className="h-4 w-4 mr-2" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => handleDelete(seq.id)}
                          className="text-destructive"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
