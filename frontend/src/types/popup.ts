export type PopupType = 'modal' | 'slide_in' | 'floating_bar' | 'full_screen';
export type PopupStatus = 'draft' | 'scheduled' | 'published' | 'paused';
export type PopupTrigger =
  | 'time' | 'exit_intent' | 'scroll' | 'page_visit' | 'click' | 'inactivity';
export type PopupPosition = 'center' | 'bottom_right' | 'bottom_left' | 'top';

export const popupTypeLabels: Record<PopupType, string> = {
  modal: 'Modal',
  slide_in: 'Slide-in',
  floating_bar: 'Floating bar',
  full_screen: 'Full screen',
};

export const popupStatusLabels: Record<PopupStatus, string> = {
  draft: 'Draft',
  scheduled: 'Scheduled',
  published: 'Published',
  paused: 'Paused',
};

export const popupTriggerLabels: Record<PopupTrigger, string> = {
  time: 'After a delay',
  exit_intent: 'On exit intent',
  scroll: 'After scrolling',
  page_visit: 'After N pages',
  click: 'When an element is clicked',
  inactivity: 'After inactivity',
};

export interface PopupDesign {
  backgroundColor: string;
  textColor: string;
  headingColor: string;
  fontFamily: string;
  borderRadius: string;
  padding: string;
  maxWidth: string;
  backdrop: boolean;
  backdropColor: string;
  position: PopupPosition;
  primaryButton: {
    backgroundColor: string;
    textColor: string;
    borderRadius: string;
    fullWidth: boolean;
  };
  closeButton: { show: boolean; color: string; delaySeconds: number };
  image: { position: 'top' | 'left' | 'background' | 'none'; height: string };
}

export interface PopupTriggers {
  type: PopupTrigger;
  delaySeconds: number;
  scrollPercent: number;
  pageVisitCount: number;
  inactivitySeconds: number;
  clickSelector: string;
}

export interface PopupTargeting {
  includeUrls: string[];
  excludeUrls: string[];
  devices: Array<'desktop' | 'mobile'>;
  visitorType: 'any' | 'new' | 'returning';
  referrers: string[];
  utm: Record<string, string>;
}

export interface PopupFrequency {
  mode: 'once_per_visitor' | 'once_per_session' | 'every_n_days' | 'every_visit';
  days: number;
}

export interface Popup {
  id: string;
  name: string;
  popup_type: PopupType;
  status: PopupStatus;
  title: string;
  description: string;
  image_url: string;
  image_alt: string;
  cta_text: string;
  cta_url: string;
  secondary_cta_text: string;
  secondary_cta_url: string;
  form: string | null;
  form_name: string | null;
  design: PopupDesign;
  triggers: PopupTriggers;
  targeting: PopupTargeting;
  frequency: PopupFrequency;
  starts_at: string | null;
  ends_at: string | null;
  /** Status alone does not say it — a schedule can hold a published popup back. */
  is_live: boolean;
  impression_count: number;
  click_count: number;
  conversion_count: number;
  conversion_rate: number;
  created_at: string;
  updated_at: string;
}

export interface PopupListResponse {
  data: Popup[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface CreatePopupData {
  name: string;
  popup_type?: PopupType;
  title?: string;
  description?: string;
  image_url?: string;
  image_alt?: string;
  cta_text?: string;
  cta_url?: string;
  secondary_cta_text?: string;
  secondary_cta_url?: string;
  form?: string | null;
  design?: Partial<PopupDesign>;
  triggers?: Partial<PopupTriggers>;
  targeting?: Partial<PopupTargeting>;
  frequency?: Partial<PopupFrequency>;
  starts_at?: string | null;
  ends_at?: string | null;
  template_id?: string | null;
}

export type UpdatePopupData = Partial<CreatePopupData> & { status?: PopupStatus };

export interface PopupTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  popup_type: PopupType;
  content: Record<string, string>;
  design: PopupDesign;
  triggers: PopupTriggers;
  /** Whether a popup made from this should capture. The form itself is the
   *  marketer's choice — we cannot guess which of theirs it should be. */
  wants_form: boolean;
  is_system: boolean;
  usage_count: number;
}

export const defaultPopupDesign: PopupDesign = {
  backgroundColor: '#ffffff',
  textColor: '#0f172a',
  headingColor: '#0f172a',
  fontFamily: 'Inter, system-ui, sans-serif',
  borderRadius: '12px',
  padding: '28px',
  maxWidth: '440px',
  backdrop: true,
  backdropColor: 'rgba(15, 23, 42, 0.55)',
  position: 'center',
  primaryButton: {
    backgroundColor: '#4f46e5',
    textColor: '#ffffff',
    borderRadius: '8px',
    fullWidth: false,
  },
  closeButton: { show: true, color: '#64748b', delaySeconds: 0 },
  image: { position: 'top', height: '160px' },
};

export const defaultPopupTriggers: PopupTriggers = {
  type: 'time',
  delaySeconds: 5,
  scrollPercent: 50,
  pageVisitCount: 2,
  inactivitySeconds: 30,
  clickSelector: '',
};

export const defaultPopupTargeting: PopupTargeting = {
  includeUrls: [],
  excludeUrls: [],
  devices: ['desktop', 'mobile'],
  visitorType: 'any',
  referrers: [],
  utm: {},
};

export const defaultPopupFrequency: PopupFrequency = {
  mode: 'once_per_visitor',
  days: 7,
};
