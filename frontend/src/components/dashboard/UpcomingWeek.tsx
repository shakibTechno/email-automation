import { Link } from 'react-router-dom';
import { format, parseISO } from 'date-fns';
import { cn } from '@/lib/utils';
import { SOURCE_BADGE } from '@/lib/calendar';
import type { CalendarSource } from '@/types/calendar';
import type { UpcomingWeek as Upcoming } from '@/types/dashboard';

interface UpcomingWeekProps {
  upcoming: Upcoming;
  todayKey: string;
}

/**
 * Singular and plural per source.
 *
 * The API's labels are plural, and "1 activities" is the kind of wrong that
 * makes a summary line look machine-written.
 */
const NOUNS: Record<string, [string, string]> = {
  campaigns: ['campaign', 'campaigns'],
  sequences: ['sequence', 'sequences'],
  activities: ['call or meeting', 'calls and meetings'],
  tasks: ['task', 'tasks'],
  deals: ['deal date', 'deal dates'],
};

/**
 * The next seven days, from the calendar's own service.
 *
 * Same letter badges as the calendar, so a chip means the same thing on both
 * screens — and the sources the viewer cannot see never reach here, because
 * the calendar filtered them already.
 */
export function UpcomingWeek({ upcoming, todayKey }: UpcomingWeekProps) {
  const summary = upcoming.sources
    .filter((s) => s.count > 0)
    .map((s) => {
      const [one, many] = NOUNS[s.key] ?? [s.label.toLowerCase(), s.label.toLowerCase()];
      return `${s.count.toLocaleString()} ${s.count === 1 ? one : many}`;
    })
    .join(' · ');

  return (
    <section className="min-w-0 flex-[999_1_420px] rounded-lg border bg-card shadow-card">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Next 7 days</h2>
        <span className="text-sm text-muted-foreground">
          {summary || 'Nothing scheduled'}
        </span>
        <Link to="/calendar" className="ml-auto text-sm font-medium underline">
          Open calendar
        </Link>
      </div>

      {/* Seven columns need room; below that the strip scrolls rather than
          squeezing each day to something unreadable. */}
      <div className="overflow-x-auto">
        <div className="grid min-w-[560px] grid-cols-7">
          {upcoming.days.map((day) => {
            const date = parseISO(day.date);
            const isToday = day.date === todayKey;
            return (
              <div
                key={day.date}
                className="flex min-h-[128px] flex-col gap-1.5 border-l p-2 first:border-l-0"
              >
                <div className="flex items-baseline gap-1.5">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                    {format(date, 'EEE')}
                  </span>
                  <span
                    className={cn(
                      'text-xs font-semibold',
                      isToday &&
                        'inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-foreground px-1.5 text-background'
                    )}
                  >
                    {format(date, 'd')}
                  </span>
                </div>

                {day.items.map((item, index) => (
                  <div
                    key={`${day.date}-${index}`}
                    className="flex items-center gap-1 overflow-hidden rounded border px-1.5 py-0.5"
                  >
                    <span
                      aria-hidden="true"
                      className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-sm bg-muted text-[9px] font-semibold"
                    >
                      {SOURCE_BADGE[item.kind as CalendarSource] ?? '·'}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-[10.5px]">
                      {item.time ? `${item.time} ` : ''}
                      {item.label}
                    </span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
