import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Edit, Play, Pause, Copy, Trash2, ArrowLeft,
  Users, Target, Clock, CheckCircle, ChevronLeft, ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import StatusBadge from '@/components/workflows/StatusBadge';
import { ExecutionDetailDrawer } from '@/components/workflows/ExecutionDetailDrawer';
import {
  useWorkflow,
  useWorkflowAnalytics,
  useWorkflowExecutions,
  useWorkflowMutations,
} from '@/hooks/useWorkflows';
import { ExecutionStatus } from '@/types/workflow';
import { cn } from '@/lib/utils';
import { formatDistanceToNow, format } from 'date-fns';

const STATUS_FILTERS: { value: ExecutionStatus | 'all'; label: string }[] = [
  { value: 'all',       label: 'All' },
  { value: 'active',    label: 'Active' },
  { value: 'waiting',   label: 'Waiting' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed',    label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

const EXEC_STATUS_STYLES: Record<ExecutionStatus, string> = {
  active:    'bg-blue-100 text-blue-700 border-blue-200',
  waiting:   'bg-amber-100 text-amber-700 border-amber-200',
  completed: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  failed:    'bg-red-100 text-red-700 border-red-200',
  cancelled: 'bg-slate-100 text-slate-600 border-slate-200',
};

const PAGE_SIZE = 15;

export default function WorkflowDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const [analyticsDays, setAnalyticsDays] = useState(30);
  const [statusFilter, setStatusFilter] = useState<ExecutionStatus | 'all'>('all');
  const [page, setPage] = useState(1);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);

  const { data: workflow, isLoading } = useWorkflow(id);
  const { data: analytics } = useWorkflowAnalytics(id, analyticsDays);
  const { data: executionsData } = useWorkflowExecutions(id, {
    status: statusFilter !== 'all' ? statusFilter : undefined,
    page,
    page_size: PAGE_SIZE,
  });
  const { deleteWorkflow, activateWorkflow, deactivateWorkflow, duplicateWorkflow } =
    useWorkflowMutations();

  const executions = executionsData?.data ?? [];
  const totalPages = executionsData?.total_pages ?? 0;
  const total = executionsData?.total ?? 0;

  const handleDelete = async () => {
    if (id) {
      await deleteWorkflow.mutateAsync(id);
      navigate('/workflows');
    }
  };

  const handleStatusFilterChange = (v: ExecutionStatus | 'all') => {
    setStatusFilter(v);
    setPage(1);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="container mx-auto py-6">
        <p className="text-center text-gray-500">Workflow not found</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">

      {/* ── header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/workflows')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{workflow.name}</h1>
              <StatusBadge status={workflow.status} />
            </div>
            {workflow.description && (
              <p className="text-gray-500 text-sm mt-0.5">{workflow.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate(`/workflows/${id}/edit`)}>
            <Edit className="h-4 w-4 mr-2" /> Edit
          </Button>
          {workflow.status === 'active' ? (
            <Button
              variant="outline"
              onClick={() => deactivateWorkflow.mutate(id!)}
              disabled={deactivateWorkflow.isPending}
            >
              <Pause className="h-4 w-4 mr-2" /> Pause
            </Button>
          ) : (
            <Button onClick={() => activateWorkflow.mutate(id!)} disabled={activateWorkflow.isPending}>
              <Play className="h-4 w-4 mr-2" /> Activate
            </Button>
          )}
          <Button
            variant="outline"
            onClick={() => duplicateWorkflow.mutate(id!)}
            disabled={duplicateWorkflow.isPending}
          >
            <Copy className="h-4 w-4 mr-2" /> Duplicate
          </Button>
          <Button variant="destructive" onClick={() => setShowDeleteDialog(true)}>
            <Trash2 className="h-4 w-4 mr-2" /> Delete
          </Button>
        </div>
      </div>

      {/* ── analytics ── */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Analytics</h2>
        <Select value={String(analyticsDays)} onValueChange={(v) => setAnalyticsDays(Number(v))}>
          <SelectTrigger className="w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Contacts Entered', value: analytics?.total_entered ?? 0, icon: Users,       color: 'text-gray-400' },
          { label: 'Active / Waiting', value: `${analytics?.active ?? 0} / ${analytics?.waiting ?? 0}`, icon: Clock, color: 'text-gray-400' },
          { label: 'Completed',        value: analytics?.completed ?? 0,     icon: CheckCircle,  color: 'text-gray-400' },
          { label: 'Goal Reached',     value: analytics?.goal_reached ?? 0,  icon: Target,       color: 'text-green-500' },
        ].map((card) => (
          <Card key={card.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">{card.label}</CardTitle>
              <card.icon className={`h-4 w-4 ${card.color}`} />
            </CardHeader>
            <CardContent>
              <p className={`text-2xl font-bold ${card.label === 'Goal Reached' ? 'text-green-600' : ''}`}>
                {card.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── executions ── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Executions</h2>
          <span className="text-sm text-muted-foreground">{total} total</span>
        </div>

        {/* status filter tabs */}
        <div className="flex gap-2 flex-wrap">
          {STATUS_FILTERS.map((sf) => (
            <button
              key={sf.value}
              onClick={() => handleStatusFilterChange(sf.value as ExecutionStatus | 'all')}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded-full border transition-colors',
                statusFilter === sf.value
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background text-muted-foreground border-border hover:bg-accent'
              )}
            >
              {sf.label}
            </button>
          ))}
        </div>

        {executions.length === 0 ? (
          <Card>
            <CardContent className="text-center py-8">
              <p className="text-gray-500">
                {statusFilter === 'all' ? 'No executions yet' : `No ${statusFilter} executions`}
              </p>
              {statusFilter === 'all' && (
                <p className="text-sm text-gray-400 mt-1">
                  {workflow.status === 'active'
                    ? 'Executions will appear here when contacts trigger this workflow'
                    : 'Activate the workflow to start processing contacts'}
                </p>
              )}
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Contact</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Current Step</TableHead>
                    <TableHead className="text-center">Steps</TableHead>
                    <TableHead>Goal</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Completed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {executions.map((execution) => (
                    <TableRow
                      key={execution.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => setSelectedExecutionId(execution.id)}
                    >
                      <TableCell>
                        <div>
                          <p className="font-medium text-sm">{execution.contact_name}</p>
                          <p className="text-xs text-muted-foreground">{execution.contact_email}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`text-xs ${EXEC_STATUS_STYLES[execution.status]}`}
                        >
                          {execution.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-[160px] truncate">
                        {execution.current_node_label || '—'}
                      </TableCell>
                      <TableCell className="text-center text-sm tabular-nums">
                        {execution.step_count}
                      </TableCell>
                      <TableCell>
                        {execution.goal_reached ? (
                          <span className="inline-flex items-center text-emerald-600 text-xs font-medium">
                            <Target className="h-3.5 w-3.5 mr-1" />
                            Reached
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {formatDistanceToNow(new Date(execution.started_at), { addSuffix: true })}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {execution.completed_at
                          ? format(new Date(execution.completed_at), 'MMM d, yyyy')
                          : '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => p - 1)}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page === totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── meta ── */}
      <div className="grid grid-cols-2 gap-4 text-sm text-gray-500">
        <div>
          Created by {workflow.created_by_name || 'Unknown'} on{' '}
          {format(new Date(workflow.created_at), 'MMM d, yyyy')}
        </div>
        <div className="text-right">
          Last updated{' '}
          {formatDistanceToNow(new Date(workflow.updated_at), { addSuffix: true })}
        </div>
      </div>

      {/* ── execution detail drawer ── */}
      <ExecutionDetailDrawer
        executionId={selectedExecutionId}
        onClose={() => setSelectedExecutionId(null)}
      />

      {/* ── delete dialog ── */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Workflow</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{workflow.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
