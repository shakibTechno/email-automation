import { Lock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SOURCE_BADGE, immovableReason, timeLabel } from '@/lib/calendar';
import type { CalendarEvent } from '@/types/calendar';

interface EventChipProps {
  event: CalendarEvent;
  onOpen: (event: CalendarEvent) => void;
  onDragStart?: (event: CalendarEvent) => void;
  onDragEnd?: () => void;
  /** True while this chip is the one being dragged. */
  dimmed?: boolean;
  className?: string;
}

/** One event, as it appears in a month cell or a week column. */
export function EventChip({
  event,
  onOpen,
  onDragStart,
  onDragEnd,
  dimmed,
  className,
}: EventChipProps) {
  const time = timeLabel(event);
  const movable = event.movable && Boolean(onDragStart);

  return (
    <button
      type="button"
      draggable={movable}
      onDragStart={movable ? () => onDragStart?.(event) : undefined}
      onDragEnd={movable ? onDragEnd : undefined}
      onClick={() => onOpen(event)}
      title={movable ? 'Drag to reschedule' : immovableReason(event)}
      className={cn(
        'flex w-full items-center gap-1.5 overflow-hidden rounded border bg-background px-1.5 py-1 text-left text-xs',
        movable ? 'cursor-grab hover:bg-accent active:cursor-grabbing' : 'cursor-pointer hover:bg-accent',
        dimmed && 'opacity-40',
        className
      )}
    >
      <span
        aria-hidden="true"
        className="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm bg-muted text-[9px] font-semibold"
      >
        {SOURCE_BADGE[event.source]}
      </span>
      {time && <span className="shrink-0 font-medium tabular-nums">{time}</span>}
      <span className="min-w-0 flex-1 truncate">{event.title}</span>
      {!event.movable && (
        <Lock aria-hidden="true" className="h-3 w-3 shrink-0 text-muted-foreground" />
      )}
      <span className="sr-only">
        {event.movable ? '' : ` — ${immovableReason(event)}`}
      </span>
    </button>
  );
}
