import { useState } from 'react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { startHour } from '@/lib/calendar';
import { EventChip } from './EventChip';
import type { CalendarEvent } from '@/types/calendar';

const HOUR_PX = 56;
const DEFAULT_FIRST_HOUR = 8;
const DEFAULT_LAST_HOUR = 18;

interface WeekGridProps {
  days: Date[];
  todayKey: string;
  eventsByDay: Map<string, CalendarEvent[]>;
  dragging: CalendarEvent | null;
  onOpenEvent: (event: CalendarEvent) => void;
  onDragStart: (event: CalendarEvent) => void;
  onDragEnd: () => void;
  onDropOnDay: (dayKey: string) => void;
}

/**
 * The window of hours to draw.
 *
 * Widened to fit whatever is actually in the week: a 07:00 send outside a
 * fixed 08:00–18:00 grid would simply be invisible, which is worse than a
 * taller page.
 */
function hourWindow(events: CalendarEvent[]): number[] {
  let first = DEFAULT_FIRST_HOUR;
  let last = DEFAULT_LAST_HOUR;
  for (const event of events) {
    if (event.all_day) continue;
    const hour = startHour(event);
    first = Math.min(first, Math.floor(hour));
    last = Math.max(last, Math.ceil(hour));
  }
  const hours: number[] = [];
  for (let h = first; h <= last; h++) hours.push(h);
  return hours;
}

export function WeekGrid({
  days,
  todayKey,
  eventsByDay,
  dragging,
  onOpenEvent,
  onDragStart,
  onDragEnd,
  onDropOnDay,
}: WeekGridProps) {
  const [over, setOver] = useState<string | null>(null);

  const all = days.flatMap((day) => eventsByDay.get(format(day, 'yyyy-MM-dd')) ?? []);
  const hours = hourWindow(all);
  const firstHour = hours[0];

  return (
    <div className="overflow-x-auto rounded-lg border">
      <div className="min-w-[780px]">
        <div
          className="grid border-b bg-muted/40"
          style={{ gridTemplateColumns: '56px repeat(7, minmax(0, 1fr))' }}
        >
          <div />
          {days.map((day) => {
            const key = format(day, 'yyyy-MM-dd');
            return (
              <div key={key} className="flex items-baseline gap-1.5 border-l px-2.5 py-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {format(day, 'EEE')}
                </span>
                {key === todayKey ? (
                  <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-foreground px-1.5 text-[11px] font-semibold text-background">
                    {format(day, 'd')}
                  </span>
                ) : (
                  <span className="text-sm font-semibold">{format(day, 'd')}</span>
                )}
              </div>
            );
          })}
        </div>

        {/* All-day lane: tasks, deal dates and sequence volume have no hour. */}
        <div
          className="grid border-b"
          style={{ gridTemplateColumns: '56px repeat(7, minmax(0, 1fr))' }}
        >
          <div className="px-2 py-2 text-right text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            All day
          </div>
          {days.map((day) => {
            const key = format(day, 'yyyy-MM-dd');
            const allDay = (eventsByDay.get(key) ?? []).filter((e) => e.all_day);
            return (
              <div
                key={key}
                onDragOver={(e) => {
                  if (!dragging) return;
                  e.preventDefault();
                  setOver(key);
                }}
                onDragLeave={() => setOver((c) => (c === key ? null : c))}
                onDrop={(e) => {
                  e.preventDefault();
                  setOver(null);
                  if (dragging) onDropOnDay(key);
                }}
                className={cn(
                  'flex min-h-[62px] flex-col gap-1 border-l p-1.5',
                  over === key && 'bg-accent ring-2 ring-inset ring-foreground'
                )}
              >
                {allDay.map((event) => (
                  <EventChip
                    key={event.id}
                    event={event}
                    onOpen={onOpenEvent}
                    onDragStart={onDragStart}
                    onDragEnd={onDragEnd}
                    dimmed={dragging?.id === event.id}
                  />
                ))}
              </div>
            );
          })}
        </div>

        {/* Hour grid */}
        <div className="grid" style={{ gridTemplateColumns: '56px repeat(7, minmax(0, 1fr))' }}>
          <div>
            {hours.map((hour) => (
              <div
                key={hour}
                className="border-t pr-2 text-right text-[10px] text-muted-foreground"
                style={{ height: HOUR_PX }}
              >
                {String(hour).padStart(2, '0')}:00
              </div>
            ))}
          </div>

          {days.map((day) => {
            const key = format(day, 'yyyy-MM-dd');
            const timed = (eventsByDay.get(key) ?? []).filter((e) => !e.all_day);
            const weekend = [0, 6].includes(day.getDay());

            return (
              <div
                key={key}
                onDragOver={(e) => {
                  if (!dragging) return;
                  e.preventDefault();
                  setOver(`t-${key}`);
                }}
                onDragLeave={() => setOver((c) => (c === `t-${key}` ? null : c))}
                onDrop={(e) => {
                  e.preventDefault();
                  setOver(null);
                  if (dragging) onDropOnDay(key);
                }}
                className={cn(
                  'relative border-l',
                  weekend && 'bg-muted/20',
                  over === `t-${key}` && 'bg-accent'
                )}
              >
                {hours.map((hour) => (
                  <div key={hour} className="border-t" style={{ height: HOUR_PX }} />
                ))}

                {timed.map((event) => {
                  const top = (startHour(event) - firstHour) * HOUR_PX;
                  const minutes = event.meta.duration ?? 30;
                  return (
                    <div
                      key={event.id}
                      className="absolute left-1 right-1"
                      style={{ top, height: Math.max(26, (minutes / 60) * HOUR_PX) }}
                    >
                      <EventChip
                        event={event}
                        onOpen={onOpenEvent}
                        onDragStart={onDragStart}
                        onDragEnd={onDragEnd}
                        dimmed={dragging?.id === event.id}
                        className="h-full items-start border-muted-foreground/50"
                      />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
