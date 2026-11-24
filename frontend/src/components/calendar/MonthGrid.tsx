import { useState } from 'react';
import { format, isSameMonth } from 'date-fns';
import { Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { EventChip } from './EventChip';
import type { CalendarEvent } from '@/types/calendar';

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const COLLAPSED_LIMIT = 3;

interface MonthGridProps {
  days: Date[];
  month: Date;
  todayKey: string;
  eventsByDay: Map<string, CalendarEvent[]>;
  dragging: CalendarEvent | null;
  canCreate: boolean;
  onOpenEvent: (event: CalendarEvent) => void;
  onDragStart: (event: CalendarEvent) => void;
  onDragEnd: () => void;
  onDropOnDay: (dayKey: string) => void;
  onNewOnDay: (dayKey: string) => void;
}

export function MonthGrid({
  days,
  month,
  todayKey,
  eventsByDay,
  dragging,
  canCreate,
  onOpenEvent,
  onDragStart,
  onDragEnd,
  onDropOnDay,
  onNewOnDay,
}: MonthGridProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [over, setOver] = useState<string | null>(null);

  const toggle = (key: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const weeks: Date[][] = [];
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7));
  }

  return (
    // Below ~700px the grid scrolls sideways rather than squeezing seven
    // columns into phone width, where nothing would be readable.
    <div className="overflow-x-auto rounded-lg border">
      <div className="min-w-[700px]">
        <div className="grid grid-cols-7 border-b bg-muted/40">
          {WEEKDAYS.map((label) => (
            <div
              key={label}
              className="px-2.5 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
            >
              {label}
            </div>
          ))}
        </div>

        {weeks.map((week) => (
          <div key={week[0].toISOString()} className="grid grid-cols-7 border-b last:border-b-0">
            {week.map((day) => {
              const key = format(day, 'yyyy-MM-dd');
              const dayEvents = eventsByDay.get(key) ?? [];
              const isOpen = expanded.has(key);
              const shown = isOpen ? dayEvents : dayEvents.slice(0, COLLAPSED_LIMIT);
              const hidden = dayEvents.length - shown.length;
              const outside = !isSameMonth(day, month);

              return (
                <div
                  key={key}
                  onDragOver={(e) => {
                    if (!dragging) return;
                    e.preventDefault();
                    setOver(key);
                  }}
                  onDragLeave={() => setOver((current) => (current === key ? null : current))}
                  onDrop={(e) => {
                    e.preventDefault();
                    setOver(null);
                    if (dragging) onDropOnDay(key);
                  }}
                  className={cn(
                    'group relative flex min-h-[120px] flex-col gap-1 border-l p-2 first:border-l-0',
                    outside && 'bg-muted/20',
                    over === key && 'bg-accent ring-2 ring-inset ring-foreground'
                  )}
                >
                  <div className="flex items-center justify-between">
                    {key === todayKey ? (
                      <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-foreground px-1.5 text-[11px] font-semibold text-background">
                        {format(day, 'd')}
                      </span>
                    ) : (
                      <span
                        className={cn(
                          'text-[11px] font-medium',
                          outside ? 'text-muted-foreground/60' : 'text-muted-foreground'
                        )}
                      >
                        {format(day, 'd')}
                      </span>
                    )}
                    {canCreate && (
                      <button
                        type="button"
                        onClick={() => onNewOnDay(key)}
                        aria-label={`Add a task on ${format(day, 'd MMMM')}`}
                        className="rounded p-0.5 text-muted-foreground opacity-0 transition hover:bg-accent focus-visible:opacity-100 group-hover:opacity-100"
                      >
                        <Plus className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>

                  {shown.map((event) => (
                    <EventChip
                      key={event.id}
                      event={event}
                      onOpen={onOpenEvent}
                      onDragStart={onDragStart}
                      onDragEnd={onDragEnd}
                      dimmed={dragging?.id === event.id}
                    />
                  ))}

                  {hidden > 0 && (
                    <button
                      type="button"
                      onClick={() => toggle(key)}
                      className="self-start text-[11px] text-muted-foreground underline"
                    >
                      +{hidden} more
                    </button>
                  )}
                  {isOpen && dayEvents.length > COLLAPSED_LIMIT && (
                    <button
                      type="button"
                      onClick={() => toggle(key)}
                      className="self-start text-[11px] text-muted-foreground underline"
                    >
                      Show less
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
