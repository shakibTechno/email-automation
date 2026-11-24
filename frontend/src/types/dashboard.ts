/** Severity of a dashboard alert. `action` is now; `soon` is this week. */
export type AlertLevel = 'action' | 'soon';

export interface DashboardAlert {
  id: string;
  level: AlertLevel;
  title: string;
  detail: string;
  action: string;
  url: string;
}

export interface AssignedItem {
  id: string;
  title: string;
  /** ISO date or datetime; null when the work has no due date. */
  due: string | null;
  overdue: boolean;
  today: boolean;
  /** Assigned within the last day. */
  is_new: boolean;
  meta: string;
  url: string;
}

export interface AssignedToMe {
  items: AssignedItem[];
  new_count: number;
  /** How many more are assigned beyond the ones listed. */
  more: number;
}

export interface UpcomingItem {
  /** The calendar source: campaigns, sequences, activities, tasks, deals. */
  kind: string;
  label: string;
  all_day: boolean;
  time: string | null;
}

export interface UpcomingWeek {
  days: { date: string; items: UpcomingItem[] }[];
  total: number;
  sources: { key: string; label: string; count: number }[];
}

export interface DashboardTile {
  key: 'deliverability' | 'engagement' | 'audience' | 'conversion';
  label: string;
  value: number;
  /** '%' or empty, for a plain count. */
  unit: string;
  /** Change against the previous period of the same length; null when there
   *  is no earlier period to compare against. */
  delta: number | null;
  delta_unit: string;
  sub: string;
  spark?: number[];
}

export interface RecentCampaign {
  id: string;
  name: string;
  status: string;
  created_at: string;
  sent_at: string | null;
}

export interface RecentSubmission {
  id: string;
  form_name: string;
  contact_email: string | null;
  created_at: string;
}

/**
 * The dashboard payload.
 *
 * A block the viewer's role cannot reach is **absent**, not empty — the same
 * rule the calendar follows, so the page can tell "nothing to show" from
 * "not yours to see".
 */
export interface DashboardData {
  days: number;
  alerts: DashboardAlert[];
  tiles: DashboardTile[];
  upcoming: UpcomingWeek | null;
  assigned?: AssignedToMe;
  recent_campaigns?: RecentCampaign[];
  recent_submissions?: RecentSubmission[];
}
