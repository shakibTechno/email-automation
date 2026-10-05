export type FormStatus = 'active' | 'inactive';
export type FormType = 'inline' | 'popup' | 'slide_in' | 'top_bar';
export type FieldType = 'text' | 'email' | 'phone' | 'dropdown' | 'checkbox' | 'radio' | 'textarea' | 'date' | 'number' | 'url' | 'hidden' | 'section' | 'divider';
export type FieldWidth = 'full' | 'half' | 'third' | 'two_thirds';

// Styling configuration
export interface FormButtonStyle {
  backgroundColor: string;
  textColor: string;
  hoverBackgroundColor: string;
  borderRadius: string;
  fontSize: string;
  fontWeight: string;
  padding: string;
  fullWidth: boolean;
}

export interface FormInputStyle {
  backgroundColor: string;
  borderWidth: string;
  borderRadius: string;
  padding: string;
  focusBorderColor: string;
  focusRingColor: string;
}

export interface FormStyling {
  primaryColor: string;
  backgroundColor: string;
  textColor: string;
  labelColor: string;
  borderColor: string;
  errorColor: string;
  successColor: string;
  fontFamily: string;
  fontSize: string;
  labelFontSize: string;
  labelFontWeight: string;
  borderRadius: string;
  fieldSpacing: string;
  padding: string;
  buttonStyle: FormButtonStyle;
  inputStyle: FormInputStyle;
}

export interface FormBranding {
  logoUrl: string;
  logoPosition: 'left' | 'center' | 'right';
  logoMaxHeight: string;
  headerText: string;
  headerFontSize: string;
  headerFontWeight: string;
  headerAlignment: 'left' | 'center' | 'right';
  footerText: string;
  footerFontSize: string;
  footerAlignment: 'left' | 'center' | 'right';
  customCss: string;
  showPoweredBy: boolean;
}

export interface FormLayout {
  formWidth: string;
  maxWidth: string;
  columns: 1 | 2 | 3;
  fieldGap: string;
  rowGap: string;
  alignment: 'left' | 'center' | 'right';
}

// Conditional logic
export interface ConditionalCondition {
  field_id: string;
  operator: 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'is_empty' | 'is_not_empty' | 'greater_than' | 'less_than';
  value: string;
}

export interface ConditionalLogic {
  enabled: boolean;
  action: 'show' | 'hide';
  logic: 'all' | 'any';
  conditions: ConditionalCondition[];
}

export interface FormField {
  id?: string;
  field_type: FieldType;
  label: string;
  placeholder?: string;
  help_text?: string;
  is_required: boolean;
  options?: string[];
  validation_rules?: Record<string, any>;
  order: number;
  contact_field_mapping?: string;
  width?: FieldWidth;
  default_value?: string;
  section_description?: string;
  conditional_logic?: ConditionalLogic;
  custom_styling?: Record<string, any>;
}

export interface Form {
  id: string;
  name: string;
  description?: string;
  status: FormStatus;
  form_type: FormType;
  submit_button_text: string;
  success_message: string;
  redirect_url?: string;
  show_gdpr_consent: boolean;
  gdpr_consent_text?: string;
  styling?: FormStyling;
  branding?: FormBranding;
  layout?: FormLayout;
  assign_tags?: { id: string; name: string; color: string }[];
  fields: FormField[];
  submission_count: number;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateFormData {
  name: string;
  description?: string;
  form_type?: FormType;
  submit_button_text?: string;
  success_message?: string;
  redirect_url?: string;
  show_gdpr_consent?: boolean;
  gdpr_consent_text?: string;
  styling?: Partial<FormStyling>;
  branding?: Partial<FormBranding>;
  layout?: Partial<FormLayout>;
  assign_tag_ids?: string[];
  fields: Omit<FormField, 'id'>[];
}

export interface UpdateFormData extends Partial<CreateFormData> {}

export interface FormFilters {
  search?: string;
  status?: FormStatus;
  form_type?: FormType;
}

export interface FormListResponse {
  data: Form[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface FormSubmission {
  id: string;
  data: { field_id: string; label: string; field_type: string; value: any }[];
  contact?: { id: string; email: string; first_name: string; last_name: string };
  ip_address?: string;
  gdpr_consent_given: boolean;
  source_url?: string;
  created_at: string;
}

export interface FormSubmissionListItem {
  id: string;
  contact_email?: string;
  contact_name?: string;
  gdpr_consent_given: boolean;
  created_at: string;
}

export interface FormSubmissionListResponse {
  data: FormSubmissionListItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PublicFormData {
  data: Record<string, any>;
  gdpr_consent_given?: boolean;
  source_url?: string;
}

export interface EmbedCodeResponse {
  embed_html: string;
  iframe_code: string;
  form_url: string;
}

export interface ShareUrlResponse {
  url: string;
}

// Default values
export const defaultFormStyling: FormStyling = {
  primaryColor: '#3b82f6',
  backgroundColor: '#ffffff',
  textColor: '#1f2937',
  labelColor: '#374151',
  borderColor: '#d1d5db',
  errorColor: '#ef4444',
  successColor: '#22c55e',
  fontFamily: 'Inter, system-ui, sans-serif',
  fontSize: '14px',
  labelFontSize: '14px',
  labelFontWeight: '500',
  borderRadius: '6px',
  fieldSpacing: '16px',
  padding: '24px',
  buttonStyle: {
    backgroundColor: '#3b82f6',
    textColor: '#ffffff',
    hoverBackgroundColor: '#2563eb',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '500',
    padding: '10px 20px',
    fullWidth: true,
  },
  inputStyle: {
    backgroundColor: '#ffffff',
    borderWidth: '1px',
    borderRadius: '6px',
    padding: '10px 12px',
    focusBorderColor: '#3b82f6',
    focusRingColor: '#3b82f633',
  },
};

export const defaultFormBranding: FormBranding = {
  logoUrl: '',
  logoPosition: 'left',
  logoMaxHeight: '48px',
  headerText: '',
  headerFontSize: '24px',
  headerFontWeight: '600',
  headerAlignment: 'left',
  footerText: '',
  footerFontSize: '12px',
  footerAlignment: 'center',
  customCss: '',
  showPoweredBy: true,
};

export const defaultFormLayout: FormLayout = {
  formWidth: '100%',
  maxWidth: '480px',
  columns: 1,
  fieldGap: '16px',
  rowGap: '16px',
  alignment: 'left',
};

export const defaultConditionalLogic: ConditionalLogic = {
  enabled: false,
  action: 'show',
  logic: 'all',
  conditions: [],
};
