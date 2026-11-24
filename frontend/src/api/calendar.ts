import apiClient from './client';
import type { CalendarPayload } from '@/types/calendar';

/** Everything dated in `[start, end]`, both as `yyyy-MM-dd`. */
export async function getCalendar(start: string, end: string): Promise<CalendarPayload> {
  const response = await apiClient.get<CalendarPayload>('/calendar', {
    params: { start, end },
  });
  return response.data;
}

/**
 * The endpoint and field a reschedule writes, per source.
 *
 * Moves go through the object's own endpoint rather than a calendar-specific
 * one: a campaign's date is `scheduled_at`, the same field the wizard writes
 * and the same one Celery Beat reads, so nothing else has to be told.
 */
const TARGETS: Record<string, { path: string; field: string; dateOnly: boolean }> = {
  campaign: { path: '/campaigns', field: 'scheduled_at', dateOnly: false },
  activity: { path: '/activities', field: 'due_date', dateOnly: false },
  task: { path: '/tasks', field: 'due_date', dateOnly: true },
  deal: { path: '/deals', field: 'close_date', dateOnly: true },
};

/**
 * Move one event to `isoValue`.
 *
 * `eventId` is the id the calendar handed out (`campaign:<uuid>`), so the
 * caller never has to know which model it was.
 */
export async function rescheduleEvent(eventId: string, isoValue: string): Promise<void> {
  const [kind, id] = eventId.split(':');
  const target = TARGETS[kind];
  if (!target || !id) {
    throw new Error('This event cannot be moved.');
  }
  await apiClient.patch(`${target.path}/${id}`, { [target.field]: isoValue });
}

export function isMoveable(eventId: string): boolean {
  return eventId.split(':')[0] in TARGETS;
}

export function movesByDateOnly(eventId: string): boolean {
  return TARGETS[eventId.split(':')[0]]?.dateOnly ?? true;
}
