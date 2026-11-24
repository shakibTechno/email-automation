import { format, parseISO } from 'date-fns';
import { Lock } from 'lucide-react';
import { SOURCE_BADGE, eventSubtitle, timeLabel } from '@/lib/calendar';
import type { CalendarEvent } from '@/types/calendar';

interface AgendaListProps {
  /** Day keys in order, each with at least one event. */
  days: string[];
  todayKey: string;
  eventsByDay: Map<string, CalendarEvent[]>;
  onOpenEvent: (event: CalendarEvent) => void;
}

/** The list view, and the one a phone opens on. */
export function AgendaList({ days, todayKey, eventsByDay, onOpenEvent }: AgendaListProps) {
  return (
    <div className="overflow-hidden rounded-lg border">
      {days.map((key) => {
        const events = eventsByDay.get(key) ?? [];
        const heading = format(parseISO(key), 'EEE d MMMM');

        return (
          <section key={key}>
            <h2 className="border-b bg-muted/40 px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {key === todayKey ? `Today — ${heading}` : heading}
            </h2>
            {events.map((event) => (
              <button
                key={event.id}
                type="button"
                onClick={() => onOpenEvent(event)}
                className="flex w-full items-start gap-3 border-b px-4 py-3 text-left last:border-b-0 hover:bg-accent"
              >
                <span className="w-14 shrink-0 pt-0.5 text-xs font-medium tabular-nums text-muted-foreground">
                  {timeLabel(event) ?? 'All day'}
                </span>
                <span
                  aria-hidden="true"
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-muted text-[10px] font-semibold"
                >
                  {SOURCE_BADGE[event.source]}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{event.title}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {eventSubtitle(event)}
                  </span>
                </span>
                {!event.movable && (
                  <Lock aria-hidden="true" className="mt-1 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                )}
              </button>
            ))}
          </section>
        );
      })}
    </div>
  );
}
