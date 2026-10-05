import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, MoreVertical, Users, RefreshCw, Copy, Trash2, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  useSegments,
  useDeleteSegment,
  useDuplicateSegment,
  useRefreshSegment,
  useExportSegmentContacts,
} from '@/hooks/useSegments';
import type { SegmentListItem, SegmentType } from '@/types/segment';

function SegmentTypeBadge({ type }: { type: SegmentType }) {
  const variants: Record<SegmentType, { label: string; className: string }> = {
    dynamic: { label: 'Dynamic', className: 'bg-info/[.14] text-info' },
    static: { label: 'Static', className: 'bg-secondary text-muted-foreground' },
  };

  const { label, className } = variants[type];
  return <Badge className={className}>{label}</Badge>;
}

function formatDate(dateString: string | null) {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatNumber(num: number) {
  return new Intl.NumberFormat().format(num);
}

export default function SegmentListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data, isLoading, error } = useSegments({
    search: search || undefined,
    segment_type: typeFilter !== 'all' ? (typeFilter as SegmentType) : undefined,
  });

  const deleteSegment = useDeleteSegment();
  const duplicateSegment = useDuplicateSegment();
  const refreshSegment = useRefreshSegment();
  const exportContacts = useExportSegmentContacts();

  const segments = data?.results || [];

  const handleDelete = () => {
    if (deleteId) {
      deleteSegment.mutate(deleteId, {
        onSuccess: () => setDeleteId(null),
      });
    }
  };

  const handleDuplicate = (segment: SegmentListItem) => {
    duplicateSegment.mutate(segment.id);
  };

  const handleRefresh = (segment: SegmentListItem) => {
    refreshSegment.mutate(segment.id);
  };

  const handleExport = (segment: SegmentListItem) => {
    exportContacts.mutate({ id: segment.id, name: segment.name });
  };

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Segments</h1>
          <p className="text-muted-foreground">
            Create and manage contact segments for targeted campaigns
          </p>
        </div>
        <Button onClick={() => navigate('/segments/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New Segment
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Segments</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(data?.count || 0)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Dynamic Segments</CardTitle>
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(segments.filter((s) => s.segment_type === 'dynamic').length)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Static Segments</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(segments.filter((s) => s.segment_type === 'static').length)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search segments..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-40">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="dynamic">Dynamic</SelectItem>
            <SelectItem value="static">Static</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-right">Contacts</TableHead>
              <TableHead>Last Updated</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  Loading segments...
                </TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-destructive">
                  Failed to load segments
                </TableCell>
              </TableRow>
            ) : segments.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <div className="text-muted-foreground">
                    {search || typeFilter !== 'all'
                      ? 'No segments match your filters'
                      : 'No segments yet. Create your first segment!'}
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              segments.map((segment) => (
                <TableRow key={segment.id}>
                  <TableCell>
                    <Link
                      to={`/segments/${segment.id}`}
                      className="font-medium hover:underline"
                    >
                      {segment.name}
                    </Link>
                    {segment.description && (
                      <p className="text-sm text-muted-foreground truncate max-w-xs">
                        {segment.description}
                      </p>
                    )}
                  </TableCell>
                  <TableCell>
                    <SegmentTypeBadge type={segment.segment_type} />
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatNumber(segment.contact_count)}
                  </TableCell>
                  <TableCell>{formatDate(segment.last_calculated_at)}</TableCell>
                  <TableCell>{formatDate(segment.created_at)}</TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => navigate(`/segments/${segment.id}`)}
                        >
                          <Users className="mr-2 h-4 w-4" />
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => navigate(`/segments/${segment.id}/edit`)}
                        >
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => handleRefresh(segment)}>
                          <RefreshCw className="mr-2 h-4 w-4" />
                          Refresh Count
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDuplicate(segment)}>
                          <Copy className="mr-2 h-4 w-4" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleExport(segment)}>
                          <Download className="mr-2 h-4 w-4" />
                          Export Contacts
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => setDeleteId(segment.id)}
                          className="text-destructive"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Segment</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this segment? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
