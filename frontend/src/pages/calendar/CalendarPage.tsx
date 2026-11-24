import { useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  addMonths,
  addWeeks,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  startOfMonth,
  startOfWeek,
} from 'date-fns';
import { CalendarDays, ChevronLeft, ChevronRight, Lock, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { SOURCE_BADGE, groupByDay } from '@/lib/calendar';
import { calendarKeys, movedToDay, useCalendar, useRescheduleEvent } from '@/hooks/useCalendar';
import { usePermissions } from '@/hooks/usePermissions';
import { useTaskMutations } from '@/hooks/useCRM';
import { MonthGrid } from '@/components/calendar/MonthGrid';
import { WeekGrid } from '@/components/calendar/WeekGrid';
import { AgendaList } from '@/components/calendar/AgendaList';
import { EventDetailsDialog } from '@/components/calendar/EventDetailsDialog';
import { TaskFormDialog } from '@/components/crm/TaskFormDialog';
import type { CalendarEvent, CalendarSource, CalendarView } from '@/types/calendar';

const HIDDEN_KEY = 'calendar-hidden-sources';
const WEEK_OPTIONS = { weekStartsOn: 1 } as const;

/** A phone opens on the agenda: a seven-column grid at 390px is unreadable. */
function initialView(): CalendarView {
  try {
    return window.matchMedia('(max-width: 640px)').matches ? 'agenda' : 'month';
  } catch {
    return 'month';
  }
}

function loadHidden(): Set<CalendarSource> {
  try {
    const raw = localStorage.getItem(HIDDEN_KEY);
    return new Set(raw ? (JSON.parse(raw) as CalendarSource[]) : []);
  } catch {
    // Private windows and blocked site data throw here. A forgotten filter is
    // not worth a blank screen.
    return new Set();
  }
}

export function CalendarPage() {
  const queryClient = useQueryClient();
  const { can } = usePermissions();
  const { createTask, isCreating } = useTaskMutations();

  const [view, setView] = useState<CalendarView>(initialView);
  const [anchor, setAnchor] = useState(() => new Date());
  const [hidden, setHidden] = useState<Set<CalendarSource>>(loadHidden);
  const [dragging, setDragging] = useState<CalendarEvent | null>(null);
  const [selected, setSelected] = useState<CalendarEvent | null>(null);
  const [newTaskDay, setNewTaskDay] = useState<string | null>(null);

  // The month view asks for the whole visible grid, so the leading and
  // trailing days of neighbouring months are not mysteriously empty.
  const { rangeStart, rangeEnd, days } = useMemo(() => {
    if (view === 'week') {
      const start = startOfWeek(anchor, WEEK_OPTIONS);
      const end = endOfWeek(anchor, WEEK_OPTIONS);
      return { rangeStart: start, rangeEnd: end, days: eachDayOfInterval({ start, end }) };
    }
    if (view === 'agenda') {
      const start = startOfMonth(anchor);
      const end = endOfMonth(anchor);
      return { rangeStart: start, rangeEnd: end, days: eachDayOfInterval({ start, end }) };
    }
    const start = startOfWeek(startOfMonth(anchor), WEEK_OPTIONS);
    const end = endOfWeek(endOfMonth(anchor), WEEK_OPTIONS);
    return { rangeStart: start, rangeEnd: end, days: eachDayOfInterval({ start, end }) };
  }, [anchor, view]);

  const startKey = format(rangeStart, 'yyyy-MM-dd');
  const endKey = format(rangeEnd, 'yyyy-MM-dd');
  const todayKey = format(new Date(), 'yyyy-MM-dd');

  const { data, isLoading, isError } = useCalendar(startKey, endKey);
  const reschedule = useRescheduleEvent(startKey, endKey);

  const visible = useMemo(
    () => (data?.events ?? []).filter((event) => !hidden.has(event.source)),
    [data?.events, hidden]
  );
  const eventsByDay = useMemo(() => groupByDay(visible), [visible]);
  const agendaDays = useMemo(
    () => [...eventsByDay.keys()].sort(),
    [eventsByDay]
  );

  const toggleSource = (source: CalendarSource) => {
    setHidden((current) => {
      const next = new Set(current);
      if (next.has(source)) next.delete(source);
      else next.add(source);
      try {
        localStorage.setItem(HIDDEN_KEY, JSON.stringify([...next]));
      } catch {
        // Nothing to do: the filter simply will not be remembered.
      }
      return next;
    });
  };

  const step = (direction: 1 | -1) => {
    setAnchor((current) =>
      view === 'week' ? addWeeks(current, direction) : addMonths(current, direction)
    );
  };

  const onDropOnDay = (dayKey: string) => {
    const event = dragging;
    setDragging(null);
    if (!event || dayKey === event.start.slice(0, 10)) return;

    // A campaign keeps its time of day when it moves, so dropping one on an
    // earlier day can land it in the past -- and the scheduler would send it
    // on its next tick, a minute later. Dragging never means "send now".
    // (new Date here compares instants, which is correct; it is only display
    // that must stay on the string the server sent.)
    if (
      event.source === 'campaigns' &&
      new Date(movedToDay(event, dayKey)).getTime() <= Date.now()
    ) {
      toast.error(
        'That moment has already passed — the campaign would send immediately. Pick a later day.'
      );
      return;
    }

    reschedule.mutate({ event, dayKey });
  };

  const title =
    view === 'week'
      ? `${format(rangeStart, 'd MMM')} – ${format(rangeEnd, 'd MMM yyyy')}`
      : format(anchor, 'MMMM yyyy');

  const canSeeAnything = (data?.sources.length ?? 0) > 0;
  const canCreateTasks = can('crm.create');

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <CalendarDays className="h-6 w-6" />
            Calendar
          </h1>
          <p className="text-muted-foreground">Everything scheduled, in one place.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div role="group" aria-label="View" className="flex overflow-hidden rounded-md border">
            {(['month', 'week', 'agenda'] as CalendarView[]).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={view === option}
                onClick={() => setView(option)}
                className={cn(
                  'px-3.5 py-1.5 text-sm capitalize transition',
                  view === option
                    ? 'bg-foreground font-semibold text-background'
                    : 'bg-background text-muted-foreground hover:bg-accent'
                )}
              >
                {option}
              </button>
            ))}
          </div>
          {canCreateTasks && (
            <Button variant="outline" onClick={() => setNewTaskDay(todayKey)}>
              <Plus className="mr-1.5 h-4 w-4" />
              New task
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" aria-label="Previous" onClick={() => step(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-[180px] text-center text-base font-semibold">{title}</div>
          <Button variant="outline" size="icon" aria-label="Next" onClick={() => step(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={() => setAnchor(new Date())}>
            Today
          </Button>
        </div>

        <div role="group" aria-label="Sources" className="flex flex-wrap gap-1.5">
          {(data?.sources ?? []).map((source) => {
            const on = !hidden.has(source.key);
            return (
              <button
                key={source.key}
                type="button"
                aria-pressed={on}
                onClick={() => toggleSource(source.key)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition',
                  on ? 'bg-muted/60 text-foreground' : 'bg-background text-muted-foreground line-through'
                )}
              >
                <span
                  aria-hidden="true"
                  className="flex h-4 w-4 items-center justify-center rounded-sm bg-muted text-[9px] font-semibold"
                >
                  {SOURCE_BADGE[source.key]}
                </span>
                {source.label}
                <span className="text-muted-foreground">{source.count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {isLoading && <Skeleton className="h-[520px] w-full rounded-lg" />}

      {isError && (
        <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          The calendar could not be loaded. Try again in a moment.
        </p>
      )}

      {data && !isLoading && (
        <>
          {!canSeeAnything ? (
            <div className="rounded-lg border border-dashed p-10 text-center">
              <p className="font-medium">Nothing here for your role</p>
              <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
                The calendar shows campaigns, sequences and CRM work. Your role
                has access to none of those, so there is nothing to put on it.
              </p>
            </div>
          ) : view === 'month' ? (
            <MonthGrid
              days={days}
              month={anchor}
              todayKey={todayKey}
              eventsByDay={eventsByDay}
              dragging={dragging}
              canCreate={canCreateTasks}
              onOpenEvent={setSelected}
              onDragStart={setDragging}
              onDragEnd={() => setDragging(null)}
              onDropOnDay={onDropOnDay}
              onNewOnDay={setNewTaskDay}
            />
          ) : view === 'week' ? (
            <WeekGrid
              days={days}
              todayKey={todayKey}
              eventsByDay={eventsByDay}
              dragging={dragging}
              onOpenEvent={setSelected}
              onDragStart={setDragging}
              onDragEnd={() => setDragging(null)}
              onDropOnDay={onDropOnDay}
            />
          ) : agendaDays.length === 0 ? (
            <div className="rounded-lg border border-dashed p-10 text-center">
              <p className="font-medium">Nothing scheduled in {format(anchor, 'MMMM')}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Schedule a campaign or add a task to see it here.
              </p>
              {canCreateTasks && (
                <Button variant="outline" className="mt-4" onClick={() => setNewTaskDay(todayKey)}>
                  <Plus className="mr-1.5 h-4 w-4" />
                  New task
                </Button>
              )}
            </div>
          ) : (
            <AgendaList
              days={agendaDays}
              todayKey={todayKey}
              eventsByDay={eventsByDay}
              onOpenEvent={setSelected}
            />
          )}

          {canSeeAnything && view !== 'agenda' && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
              <span className="font-semibold text-foreground">Legend</span>
              {(data.sources ?? []).map((source) => (
                <span key={source.key} className="inline-flex items-center gap-1.5">
                  <span
                    aria-hidden="true"
                    className="flex h-4 w-4 items-center justify-center rounded-sm bg-muted text-[9px] font-semibold"
                  >
                    {SOURCE_BADGE[source.key]}
                  </span>
                  {source.label}
                </span>
              ))}
              <span className="inline-flex items-center gap-1.5">
                <Lock aria-hidden="true" className="h-3 w-3" />
                Cannot be moved
              </span>
              <span className="ml-auto">Times in {data.timezone}</span>
            </div>
          )}
        </>
      )}

      <EventDetailsDialog
        event={selected}
        timezone={data?.timezone ?? 'UTC'}
        onOpenChange={(open) => !open && setSelected(null)}
      />

      {newTaskDay && (
        <TaskFormDialog
          open
          onOpenChange={(open) => !open && setNewTaskDay(null)}
          isLoading={isCreating}
          initialData={{ due_date: newTaskDay }}
          onSubmit={async (values) => {
            await createTask(values);
            // useTaskMutations only knows about its own keys.
            queryClient.invalidateQueries({ queryKey: calendarKeys.all });
            setNewTaskDay(null);
          }}
        />
      )}
    </div>
  );
}
