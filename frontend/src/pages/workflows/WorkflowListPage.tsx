import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Play, Pause, Copy, Trash2, Eye, MoreHorizontal } from 'lucide-react';
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
  DropdownMenuTrigger,
  DropdownMenuSeparator,
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
import StatusBadge from '@/components/workflows/StatusBadge';
import WorkflowTemplateDialog from '@/components/workflows/dialogs/WorkflowTemplateDialog';
import { useWorkflows, useWorkflowMutations } from '@/hooks/useWorkflows';
import { WorkflowStatus, WorkflowListItem } from '@/types/workflow';
import { formatDistanceToNow } from 'date-fns';

export default function WorkflowListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [deleteWorkflow, setDeleteWorkflow] = useState<WorkflowListItem | null>(null);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);

  const { data, isLoading } = useWorkflows({
    search: search || undefined,
    status: statusFilter !== 'all' ? (statusFilter as WorkflowStatus) : undefined,
  });

  const {
    deleteWorkflow: deleteWorkflowMutation,
    activateWorkflow,
    deactivateWorkflow,
    duplicateWorkflow,
  } = useWorkflowMutations();

  const workflows = data?.data || [];

  const handleDelete = async () => {
    if (deleteWorkflow) {
      await deleteWorkflowMutation.mutateAsync(deleteWorkflow.id);
      setDeleteWorkflow(null);
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Workflows</h1>
          <p className="text-muted-foreground">
            Automate your marketing with visual workflows
          </p>
        </div>
        <Button onClick={() => setShowTemplateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Workflow
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-subtle-foreground" />
          <Input
            placeholder="Search workflows..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-info" />
        </div>
      ) : workflows.length === 0 ? (
        <div className="text-center py-12 border rounded-lg">
          <p className="text-muted-foreground mb-4">No workflows found</p>
          <Button onClick={() => setShowTemplateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create your first workflow
          </Button>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Entered</TableHead>
                <TableHead className="text-right">Completed</TableHead>
                <TableHead className="text-right">Goal Reached</TableHead>
                <TableHead>Last Updated</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workflows.map((workflow) => (
                <TableRow
                  key={workflow.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/workflows/${workflow.id}`)}
                >
                  <TableCell>
                    <div>
                      <p className="font-medium">{workflow.name}</p>
                      {workflow.description && (
                        <p className="text-sm text-muted-foreground truncate max-w-[300px]">
                          {workflow.description}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={workflow.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    {workflow.contacts_entered}
                  </TableCell>
                  <TableCell className="text-right">
                    {workflow.contacts_completed}
                  </TableCell>
                  <TableCell className="text-right">
                    {workflow.contacts_goal_reached}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDistanceToNow(new Date(workflow.updated_at), {
                      addSuffix: true,
                    })}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/workflows/${workflow.id}/edit`);
                          }}
                        >
                          <Eye className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        {workflow.status === 'active' ? (
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              deactivateWorkflow.mutate(workflow.id);
                            }}
                          >
                            <Pause className="h-4 w-4 mr-2" />
                            Pause
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              activateWorkflow.mutate(workflow.id);
                            }}
                          >
                            <Play className="h-4 w-4 mr-2" />
                            Activate
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            duplicateWorkflow.mutate(workflow.id);
                          }}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteWorkflow(workflow);
                          }}
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

      {/* Delete confirmation dialog */}
      <AlertDialog
        open={!!deleteWorkflow}
        onOpenChange={() => setDeleteWorkflow(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Workflow</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deleteWorkflow?.name}"? This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Template selection dialog */}
      <WorkflowTemplateDialog
        open={showTemplateDialog}
        onOpenChange={setShowTemplateDialog}
      />
    </div>
  );
}
