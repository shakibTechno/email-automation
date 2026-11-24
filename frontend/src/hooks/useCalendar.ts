import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as calendarApi from '@/api/calendar';
import type { CalendarEvent, CalendarPayload } from '@/types/calendar';

export const calendarKeys = {
  all: ['calendar'] as const,
  range: (start: string, end: string) => [...calendarKeys.all, start, end] as const,
};

export function useCalendar(start: string, end: string) {
  return useQuery({
    queryKey: calendarKeys.range(start, end),
    queryFn: () => calendarApi.getCalendar(start, end),
    // Scheduled work does not change by the second, and paging back and forth
    // between months should not refetch what was just read.
    staleTime: 60 * 1000,
  });
}

/**
 * Keeps the clock and moves the date.
 *
 * `2026-12-03T09:00:00+06:00` dropped on the 5th becomes
 * `2026-12-05T09:00:00+06:00` — the offset and the time of day are carried
 * over verbatim from the string the server sent, so nothing is re-derived
 * through a Date and nothing shifts into the browser's timezone.
 */
export function movedToDay(event: CalendarEvent, dayKey: string): string {
  if (event.all_day) return dayKey;
  return `${dayKey}${event.start.slice(10)}`;
}

export function useRescheduleEvent(start: string, end: string) {
  const queryClient = useQueryClient();
  const key = calendarKeys.range(start, end);

  return useMutation({
    mutationFn: ({ event, dayKey }: { event: CalendarEvent; dayKey: string }) =>
      calendarApi.rescheduleEvent(event.id, movedToDay(event, dayKey)),

    // The chip moves under the cursor, not after the round trip. A drop that
    // visually snaps back while the request is in flight reads as a failure.
    onMutate: async ({ event, dayKey }) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<CalendarPayload>(key);
      if (previous) {
        queryClient.setQueryData<CalendarPayload>(key, {
          ...previous,
          events: previous.events.map((e) =>
            e.id === event.id ? { ...e, start: movedToDay(e, dayKey) } : e
          ),
        });
      }
      return { previous };
    },

    onError: (error: any, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(key, context.previous);
      }
      // The server's reason, which is usually something the user can act on:
      // a campaign that is already sending, or a date in the past.
      const detail =
        error?.details && typeof error.details === 'object'
          ? Object.values(error.details).flat()[0]
          : null;
      toast.error(String(detail || error?.error || error?.message || 'Could not move it'));
    },

    onSuccess: () => {
      toast.success('Rescheduled');
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: calendarKeys.all });
    },
  });
}
