import { AlertTriangle } from 'lucide-react';
import type { WorkflowProblem } from '@/types/workflow';

interface WorkflowProblemsProps {
  problems: WorkflowProblem[];
  className?: string;
}

/**
 * What the canvas cannot say for itself.
 *
 * A step nothing leads to looks identical to a connected one, and a run that
 * walks past it finishes as "completed" with no error — so a workflow can be
 * active and quietly skipping half of itself. This is the only place that says
 * so, which is why it sits above the analytics rather than below them.
 */
export function WorkflowProblems({ problems, className }: WorkflowProblemsProps) {
  if (problems.length === 0) return null;

  return (
    <div
      role="status"
      className={`rounded-lg border border-foreground/40 bg-muted/40 p-3.5 ${className ?? ''}`}
    >
      <div className="flex items-center gap-2">
        <AlertTriangle aria-hidden="true" className="h-4 w-4 shrink-0" />
        <h2 className="text-sm font-semibold">
          {problems.length === 1
            ? 'This workflow has a gap'
            : `This workflow has ${problems.length} gaps`}
        </h2>
      </div>
      <ul className="mt-1.5 space-y-1 pl-6 text-sm text-muted-foreground">
        {problems.map((problem) => (
          <li key={problem.code} className="list-disc">
            {problem.message}
          </li>
        ))}
      </ul>
      <p className="mt-2 pl-6 text-xs text-muted-foreground">
        Contacts still run the connected part and finish there, which is why
        those runs read as completed.
      </p>
    </div>
  );
}
