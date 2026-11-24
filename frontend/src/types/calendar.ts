/** The five things the calendar reads. */
export type CalendarSource =
  | 'campaigns'
  | 'sequences'
  | 'activities'
  | 'tasks'
  | 'deals';

export interface CalendarEvent {
  /** `<source-singular>:<uuid>`, which is what a reschedule is addressed by. */
  id: string;
  source: CalendarSource;
  title: string;
  /**
   * Already in the viewer's timezone: `2026-12-03T09:00:00+06:00` for a timed
   * event, `2026-12-01` for an all-day one.
   *
   * Read it as a string, never through `new Date()` for display — the server
   * has done the conversion, and parsing it back into a Date shifts it again
   * into whatever timezone the browser happens to be in.
   */
  start: string;
  end: string | null;
  all_day: boolean;
  status: string;
  /** Where the real object lives. */
  url: string;
  movable: boolean;
  meta: {
    recipients?: number;
    emails?: number;
    duration?: number | null;
    kind?: string;
    deal?: string | null;
    assignee?: string | null;
    priority?: string;
    value?: string;
    currency?: string;
  };
}

export interface CalendarSourceSummary {
  key: CalendarSource;
  label: string;
  count: number;
}

export interface CalendarPayload {
  start: string;
  end: string;
  timezone: string;
  /** Only the sources this viewer may see. An absent one is not an empty one. */
  sources: CalendarSourceSummary[];
  events: CalendarEvent[];
}

export type CalendarView = 'month' | 'week' | 'agenda';
