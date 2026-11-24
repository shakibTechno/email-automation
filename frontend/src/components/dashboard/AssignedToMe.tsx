import { Link } from 'react-router-dom';
import { format, parseISO } from 'date-fns';
import { cn } from '@/lib/utils';
import type { AssignedItem, AssignedToMe as Assigned } from '@/types/dashboard';

interface AssignedToMeProps {
  assigned: Assigned;
}

/** Overdue, today, or the date — whichever is the most useful thing to say. */
function dueLabel(item: AssignedItem): string {
  if (item.overdue) return 'Late';
  if (item.today) return 'Today';
  if (!item.due) return 'No date';
  try {
    return format(parseISO(item.due), 'EEE d MMM');
  } catch {
    return item.due;
  }
}

/**
 * The only block on the dashboard that answers "what is mine".
 *
 * Tasks and the calls someone booked for you, in the order you would work
 * through them. It stays on screen when empty, because "nothing is assigned to
 * you" is an answer; only the alerts card disappears.
 */
export function AssignedToMe({ assigned }: AssignedToMeProps) {
  const { items, new_count: newCount, more } = assigned;

  return (
    <section className="flex min-w-0 flex-1 basis-[340px] flex-col rounded-lg border bg-card shadow-card">
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Assigned to me</h2>
        {newCount > 0 && (
          <span className="rounded-full bg-foreground px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-background">
            {newCount} new
          </span>
        )}
        <Link to="/crm" className="ml-auto text-sm font-medium underline">
          All tasks
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="flex flex-1 items-center justify-center px-5 py-10 text-center">
          <p className="text-sm text-muted-foreground">
            <span className="block font-medium text-foreground">
              Nothing assigned to you
            </span>
            Tasks and calls someone gives you show up here first.
          </p>
        </div>
      ) : (
        <>
          {items.map((item) => (
            <Link
              key={item.id}
              to={item.url}
              className="flex items-baseline gap-3 border-b px-4 py-2.5 last:border-b-0 hover:bg-accent"
            >
              <span
                className={cn(
                  'min-w-[58px] shrink-0 rounded border px-1.5 py-0.5 text-center text-[10px] font-semibold uppercase tracking-wider',
                  item.is_new
                    ? 'border-foreground bg-foreground text-background'
                    : 'border-muted-foreground/50 text-foreground'
                )}
              >
                {item.is_new ? 'New' : dueLabel(item)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{item.title}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {[item.is_new ? dueLabel(item) : null, item.meta]
                    .filter(Boolean)
                    .join(' · ')}
                </span>
              </span>
            </Link>
          ))}
          {more > 0 && (
            <div className="px-4 py-2">
              <Link to="/crm" className="text-xs underline">
                {more} more assigned to you
              </Link>
            </div>
          )}
        </>
      )}
    </section>
  );
}
