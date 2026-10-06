import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface WizardStep {
  id: number;
  label: string;
}

interface StepIndicatorProps {
  steps: WizardStep[];
  current: number;
  /** Return false to block navigating to a step. Completed steps are clickable. */
  onStepClick?: (id: number) => void;
  className?: string;
}

/**
 * Shared wizard rail. The campaign wizard and the form builder each had their
 * own — one a row of filled pills, the other chevron-separated text — so the
 * same concept looked like two different products. A numbered circle that
 * becomes a tick once passed carries both position and progress.
 */
export const StepIndicator = ({ steps, current, onStepClick, className }: StepIndicatorProps) => (
  <ol className={cn('flex flex-wrap items-center', className)}>
    {steps.map((step, i) => {
      const done = current > step.id;
      const active = current === step.id;
      const reachable = done || active;

      return (
        <li key={step.id} className="flex items-center">
          <button
            type="button"
            disabled={!reachable || !onStepClick}
            aria-current={active ? 'step' : undefined}
            onClick={() => reachable && onStepClick?.(step.id)}
            className={cn(
              'flex items-center gap-2 pr-3 text-left',
              reachable && onStepClick ? 'cursor-pointer' : 'cursor-default'
            )}
          >
            <span
              className={cn(
                'grid h-[22px] w-[22px] flex-none place-items-center rounded-full border font-mono text-[10px] transition-colors',
                active && 'border-transparent bg-brand-fill text-brand-ink',
                done && 'border-transparent bg-brand/[.14] text-brand',
                !active && !done && 'border-border text-subtle-foreground'
              )}
            >
              {done ? <Check className="h-3 w-3" /> : step.id}
            </span>
            <span
              className={cn(
                'whitespace-nowrap text-[12.5px] font-semibold',
                active && 'text-foreground',
                done && 'text-muted-foreground',
                !active && !done && 'text-subtle-foreground'
              )}
            >
              {step.label}
            </span>
          </button>

          {i < steps.length - 1 && (
            <span
              aria-hidden="true"
              className={cn('mr-3 h-px w-6', done ? 'bg-brand/40' : 'bg-border')}
            />
          )}
        </li>
      );
    })}
  </ol>
);
