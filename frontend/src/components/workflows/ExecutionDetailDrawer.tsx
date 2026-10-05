import { useNavigate } from 'react-router-dom';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  FileText, Tag, UserPlus, MailOpen, MousePointerClick, Calendar,
  TrendingUp, Mail, UserCog, Clock, Target, GitBranch,
  AlertCircle,
  ExternalLink, Ban, Webhook,
} from 'lucide-react';
import { useWorkflowExecution, useWorkflowExecutionMutations } from '@/hooks/useWorkflowExecutions';
import { WorkflowExecutionStep } from '@/types/workflow';
import { format, formatDistanceToNow } from 'date-fns';

// ── node-type → icon + colours ────────────────────────────────────────────────
const NODE_UI: Record<string, { icon: React.ElementType; bg: string; fg: string }> = {
  trigger_form_submission:     { icon: FileText,          bg: 'bg-blue-100',   fg: 'text-blue-600' },
  trigger_tag_added:           { icon: Tag,               bg: 'bg-blue-100',   fg: 'text-blue-600' },
  trigger_tag_removed:         { icon: Tag,               bg: 'bg-blue-100',   fg: 'text-blue-600' },
  trigger_contact_created:     { icon: UserPlus,          bg: 'bg-blue-100',   fg: 'text-blue-600' },
  trigger_email_opened:        { icon: MailOpen,          bg: 'bg-blue-100',   fg: 'text-blue-600' },
  trigger_email_clicked:       { icon: MousePointerClick, bg: 'bg-blue-100',   fg: 'text-blue-600' },
  trigger_date_field:          { icon: Calendar,          bg: 'bg-blue-100',   fg: 'text-blue-600' },
  trigger_lead_score_threshold:{ icon: TrendingUp,        bg: 'bg-blue-100',   fg: 'text-blue-600' },
  action_send_email:           { icon: Mail,              bg: 'bg-green-100',  fg: 'text-green-600' },
  action_add_tag:              { icon: Tag,               bg: 'bg-green-100',  fg: 'text-green-600' },
  action_remove_tag:           { icon: Tag,               bg: 'bg-green-100',  fg: 'text-green-600' },
  action_update_contact:       { icon: UserCog,           bg: 'bg-green-100',  fg: 'text-green-600' },
  action_wait:                 { icon: Clock,             bg: 'bg-green-100',  fg: 'text-green-600' },
  action_webhook:              { icon: Webhook,           bg: 'bg-green-100',  fg: 'text-green-600' },
  action_goal:                 { icon: Target,            bg: 'bg-purple-100', fg: 'text-purple-600' },
  action_update_lead_score:    { icon: TrendingUp,        bg: 'bg-green-100',  fg: 'text-green-600' },
  condition_if_else:           { icon: GitBranch,         bg: 'bg-amber-100',  fg: 'text-amber-600' },
};

const FALLBACK_NODE_UI = { icon: AlertCircle, bg: 'bg-slate-100', fg: 'text-slate-500' };
function nodeUi(type: string | null) {
  return (type ? NODE_UI[type] : undefined) ?? FALLBACK_NODE_UI;
}

// ── step status ───────────────────────────────────────────────────────────────
const STEP_STATUS: Record<string, { label: string; className: string; dot: string }> = {
  completed: { label: 'Done',    className: 'bg-emerald-100 text-emerald-700 border-emerald-200', dot: 'bg-emerald-500' },
  failed:    { label: 'Failed',  className: 'bg-red-100 text-red-700 border-red-200',             dot: 'bg-red-500' },
  running:   { label: 'Running', className: 'bg-blue-100 text-blue-700 border-blue-200',           dot: 'bg-blue-500 animate-pulse' },
  pending:   { label: 'Pending', className: 'bg-slate-100 text-slate-600 border-slate-200',        dot: 'bg-slate-300' },
  skipped:   { label: 'Skipped', className: 'bg-amber-100 text-amber-700 border-amber-200',        dot: 'bg-amber-400' },
};

const EXEC_STATUS: Record<string, { label: string; className: string }> = {
  active:    { label: 'Active',     className: 'bg-blue-100 text-blue-700 border-blue-200' },
  waiting:   { label: 'Waiting',    className: 'bg-amber-100 text-amber-700 border-amber-200' },
  completed: { label: 'Completed',  className: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  failed:    { label: 'Failed',     className: 'bg-red-100 text-red-700 border-red-200' },
  cancelled: { label: 'Cancelled',  className: 'bg-slate-100 text-slate-600 border-slate-200' },
};

// ── helpers ───────────────────────────────────────────────────────────────────
function duration(start: string | null, end: string | null): string {
  if (!start || !end) return '';
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

function stepSummary(step: WorkflowExecutionStep): string | null {
  const out = step.output_data as Record<string, unknown>;
  if (!out || Object.keys(out).length === 0) return null;
  if (out.email_sent !== undefined) return `Email sent: ${out.email_sent ? 'yes' : 'no'}`;
  if (out.tag_name) return `Tag: ${out.tag_name}`;
  if (out.status_code) return `HTTP ${out.status_code}`;
  if (out.score_delta !== undefined) return `Score Δ ${out.score_delta}`;
  return null;
}

// ── step row ──────────────────────────────────────────────────────────────────
function StepRow({ step, isLast }: { step: WorkflowExecutionStep; isLast: boolean }) {
  const { icon: Icon, bg, fg } = nodeUi(step.node_type);
  const ss = STEP_STATUS[step.status] ?? STEP_STATUS.pending;
  const dur = duration(step.started_at, step.completed_at);
  const summary = stepSummary(step);

  return (
    <div className="flex gap-3">
      {/* icon + vertical connector */}
      <div className="flex flex-col items-center flex-shrink-0">
        <div className={`h-8 w-8 rounded-full flex items-center justify-center ${bg}`}>
          <Icon className={`h-4 w-4 ${fg}`} />
        </div>
        {!isLast && <div className="w-px flex-1 bg-border mt-1 mb-1 min-h-[16px]" />}
      </div>

      {/* content */}
      <div className="pb-4 min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium">
                {step.node_label || (step.node_type ? step.node_type.replace(/_/g, ' ') : 'Unknown step')}
              </span>
              <Badge variant="outline" className={`text-xs h-5 ${ss.className}`}>
                {ss.label}
              </Badge>
              {step.branch_taken && (
                <Badge variant="outline" className={`text-xs h-5 ${
                  step.branch_taken === 'true'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}>
                  {step.branch_taken === 'true' ? '✓ True' : '✗ False'}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-muted-foreground capitalize">
                {step.node_type ? step.node_type.replace(/_/g, ' ') : 'deleted node'}
              </span>
              {dur && (
                <>
                  <span className="text-xs text-muted-foreground">·</span>
                  <span className="text-xs text-muted-foreground font-mono">{dur}</span>
                </>
              )}
              {summary && (
                <>
                  <span className="text-xs text-muted-foreground">·</span>
                  <span className="text-xs text-muted-foreground">{summary}</span>
                </>
              )}
            </div>
          </div>
          {step.started_at && (
            <span className="text-xs text-muted-foreground flex-shrink-0 pt-0.5">
              {format(new Date(step.started_at), 'HH:mm:ss')}
            </span>
          )}
        </div>
        {step.error_message && (
          <div className="mt-1.5 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700 font-mono">
            {step.error_message}
          </div>
        )}
      </div>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────
interface Props {
  executionId: string | null;
  onClose: () => void;
}

export function ExecutionDetailDrawer({ executionId, onClose }: Props) {
  const navigate = useNavigate();
  const { data: execution, isLoading, error } = useWorkflowExecution(executionId ?? undefined);
  const { cancelExecution } = useWorkflowExecutionMutations();

  const canCancel = execution?.status === 'active' || execution?.status === 'waiting';
  const execStatus = EXEC_STATUS[execution?.status ?? ''] ?? EXEC_STATUS.active;
  const totalDur = execution ? duration(execution.started_at, execution.completed_at) : '';

  const triggerEntries = execution?.trigger_data
    ? Object.entries(execution.trigger_data).filter(([, v]) => v !== null && v !== '')
    : [];

  return (
    <Sheet open={!!executionId} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="mb-4">
          <SheetTitle>Execution Log</SheetTitle>
        </SheetHeader>

        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex gap-3">
                <Skeleton className="h-8 w-8 rounded-full flex-shrink-0" />
                <div className="flex-1 space-y-1.5 pt-1">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            Could not load execution details. Please try again.
          </div>
        ) : execution ? (
          <div className="space-y-5">

            {/* ── execution header ── */}
            <div className="rounded-lg border p-4 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <button
                    className="text-sm font-semibold hover:underline flex items-center gap-1"
                    onClick={() => { navigate(`/contacts/${execution.contact}`); onClose(); }}
                  >
                    {execution.contact_name}
                    <ExternalLink className="h-3 w-3" />
                  </button>
                  <div className="text-xs text-muted-foreground font-mono">
                    {execution.contact_email}
                  </div>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <Badge variant="outline" className={`text-xs ${execStatus.className}`}>
                    {execStatus.label}
                  </Badge>
                  {execution.goal_reached && (
                    <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-200">
                      <Target className="h-3 w-3 mr-1" />
                      Goal
                    </Badge>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-muted-foreground">Started</div>
                  <div className="font-medium">
                    {format(new Date(execution.started_at), 'MMM d, HH:mm:ss')}
                  </div>
                </div>
                {execution.completed_at ? (
                  <div>
                    <div className="text-muted-foreground">Completed</div>
                    <div className="font-medium">
                      {format(new Date(execution.completed_at), 'MMM d, HH:mm:ss')}
                    </div>
                  </div>
                ) : execution.resume_at ? (
                  <div>
                    <div className="text-muted-foreground">Resumes</div>
                    <div className="font-medium">
                      {formatDistanceToNow(new Date(execution.resume_at), { addSuffix: true })}
                    </div>
                  </div>
                ) : null}
                {totalDur && (
                  <div>
                    <div className="text-muted-foreground">Duration</div>
                    <div className="font-medium font-mono">{totalDur}</div>
                  </div>
                )}
                <div>
                  <div className="text-muted-foreground">Steps</div>
                  <div className="font-medium">
                    {execution.steps.filter((s) => s.status === 'completed').length} / {execution.steps.length}
                  </div>
                </div>
              </div>

              {execution.error_message && (
                <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700 font-mono">
                  {execution.error_message}
                </div>
              )}

              {canCancel && (
                <Button
                  variant="destructive"
                  size="sm"
                  className="w-full"
                  disabled={cancelExecution.isPending}
                  onClick={() => {
                    cancelExecution.mutate(execution.id);
                    onClose();
                  }}
                >
                  <Ban className="h-3.5 w-3.5 mr-1.5" />
                  Cancel Execution
                </Button>
              )}
            </div>

            {/* ── trigger data ── */}
            {triggerEntries.length > 0 && (
              <div>
                <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">
                  Trigger Data
                </div>
                <div className="rounded-md border bg-muted/40 px-3 py-2 space-y-1">
                  {triggerEntries.map(([k, v]) => (
                    <div key={k} className="flex gap-2 text-xs">
                      <span className="text-muted-foreground min-w-[100px] font-mono">{k}</span>
                      <span className="font-medium truncate">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── step log ── */}
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
                Step Log
              </div>
              {execution.steps.length === 0 ? (
                <p className="text-sm text-muted-foreground">No steps recorded yet.</p>
              ) : (
                <div>
                  {execution.steps.map((step, idx) => (
                    <StepRow
                      key={step.id}
                      step={step}
                      isLast={idx === execution.steps.length - 1}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
