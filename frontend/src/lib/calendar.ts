import type { CalendarEvent, CalendarSource } from '@/types/calendar';

/**
 * The letter that marks an event's source.
 *
 * Type is carried by a letter and the legend rather than by colour alone, so
 * the calendar still reads for someone who cannot tell two hues apart.
 */
export const SOURCE_BADGE: Record<CalendarSource, string> = {
  campaigns: 'C',
  sequences: 'S',
  activities: 'A',
  tasks: 'T',
  deals: 'D',
};

export const SOURCE_NAME: Record<CalendarSource, string> = {
  campaigns: 'Campaign',
  sequences: 'Sequence',
  activities: 'Activity',
  tasks: 'Task',
  deals: 'Deal',
};

/**
 * Which day an event belongs to, as `yyyy-MM-dd`.
 *
 * Taken off the front of the string the server sent, which is already in the
 * viewer's timezone. Going through `new Date()` would re-interpret it in the
 * browser's zone and move events across midnight.
 */
export function dayKey(event: CalendarEvent): string {
  return event.start.slice(0, 10);
}

/** `09:00`, or null for an all-day event. */
export function timeLabel(event: CalendarEvent): string | null {
  return event.all_day ? null : event.start.slice(11, 16);
}

/** The hour an event starts on, as a fraction (09:30 → 9.5). */
export function startHour(event: CalendarEvent): number {
  const label = timeLabel(event);
  if (!label) return 0;
  const [hours, minutes] = label.split(':').map(Number);
  return hours + minutes / 60;
}

export function eventSubtitle(event: CalendarEvent): string {
  const { meta } = event;
  switch (event.source) {
    case 'campaigns':
      return [
        event.status,
        meta.recipients ? `${meta.recipients.toLocaleString()} recipients` : null,
      ]
        .filter(Boolean)
        .join(' · ');
    case 'sequences':
      return `${(meta.emails ?? 0).toLocaleString()} emails due`;
    case 'activities':
      return [
        meta.kind,
        meta.duration ? `${meta.duration} min` : null,
        meta.deal ? `Deal: ${meta.deal}` : null,
      ]
        .filter(Boolean)
        .join(' · ');
    case 'tasks':
      return [
        meta.priority ? `${meta.priority} priority` : null,
        meta.assignee,
        meta.deal ? `Deal: ${meta.deal}` : null,
      ]
        .filter(Boolean)
        .join(' · ');
    case 'deals':
      return meta.value ? `Expected close · ${meta.currency} ${meta.value}` : 'Expected close';
    default:
      return '';
  }
}

/** Why an event cannot be dragged, for the title attribute. */
export function immovableReason(event: CalendarEvent): string {
  if (event.source === 'sequences') {
    return 'A day of sends is a total, not one thing to move';
  }
  if (event.source === 'campaigns' && event.status === 'sending') {
    return 'Already sending — cancel it on the campaign page first';
  }
  if (event.status === 'sent' || event.status === 'done' || event.status === 'completed') {
    return 'Already done';
  }
  return 'This one cannot be moved';
}

export function groupByDay(events: CalendarEvent[]): Map<string, CalendarEvent[]> {
  const byDay = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const key = dayKey(event);
    const existing = byDay.get(key);
    if (existing) {
      existing.push(event);
    } else {
      byDay.set(key, [event]);
    }
  }
  return byDay;
}
