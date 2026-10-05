export type PlanType = 'free' | 'starter' | 'professional' | 'business' | 'enterprise';
export type BillingInterval = 'month' | 'year';
export type SubscriptionStatus = 'trialing' | 'active' | 'past_due' | 'cancelled' | 'expired' | 'incomplete';
export type InvoiceStatus = 'draft' | 'open' | 'paid' | 'void' | 'uncollectible';
export type CardBrand = 'visa' | 'mastercard' | 'amex' | 'discover' | 'other';

export interface Plan {
  id: string;
  name: string;
  plan_type: PlanType;
  interval: BillingInterval;
  price: string;
  annual_price: string;
  monthly_equivalent: string;
  max_contacts: number;
  max_emails_per_month: number;
  max_automations: number;
  max_landing_pages: number;
  max_users: number;
  has_ab_testing: boolean;
  has_advanced_segmentation: boolean;
  has_lead_scoring: boolean;
  has_crm: boolean;
  has_api_access: boolean;
  has_custom_reports: boolean;
  has_sms_marketing: boolean;
  has_ai_features: boolean;
  has_dedicated_ip: boolean;
  has_sso: boolean;
  has_white_labeling: boolean;
  remove_watermark: boolean;
  is_active: boolean;
  is_popular: boolean;
  sort_order: number;
}

export interface Subscription {
  id: string;
  plan: Plan;
  status: SubscriptionStatus;
  interval: BillingInterval;
  stripe_customer_id: string;
  has_stripe_subscription: boolean;
  current_period_start: string | null;
  current_period_end: string | null;
  trial_start: string | null;
  trial_end: string | null;
  cancel_at_period_end: boolean;
  cancelled_at: string | null;
  cancellation_reason: string;
  emails_sent_this_month: number;
  usage_reset_date: string | null;
  is_active: boolean;
  is_trialing: boolean;
  trial_days_remaining: number;
  is_on_free_plan: boolean;
  contacts_usage_percent: number;
  emails_usage_percent: number;
  created_at: string;
  updated_at: string;
}

export interface PaymentMethod {
  id: string;
  card_brand: CardBrand;
  card_last4: string;
  card_exp_month: number;
  card_exp_year: number;
  is_default: boolean;
  is_expired: boolean;
  created_at: string;
}

export interface Invoice {
  id: string;
  number: string;
  status: InvoiceStatus;
  currency: string;
  subtotal: number;
  tax: number;
  total: number;
  amount_paid: number;
  amount_due: number;
  total_dollars: string;
  subtotal_dollars: string;
  tax_dollars: string;
  amount_due_dollars: string;
  invoice_date: string | null;
  due_date: string | null;
  paid_at: string | null;
  stripe_hosted_invoice_url: string;
  stripe_invoice_pdf: string;
  description: string;
  line_items: InvoiceLineItem[];
  created_at: string;
}

export interface InvoiceLineItem {
  description: string;
  amount: number;
  quantity: number;
  period_start: number | null;
  period_end: number | null;
}

export interface BillingEvent {
  id: string;
  event_type: string;
  description: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface BillingOverview {
  plan: Plan;
  subscription: Subscription;
  contact_count: number;
  contacts_limit: number;
  contacts_usage_percent: number;
  emails_sent: number;
  emails_limit: number;
  emails_usage_percent: number;
  trial_days_remaining: number;
  is_trialing: boolean;
  cancel_at_period_end: boolean;
  current_period_end: string | null;
}

export interface UsageLimit {
  allowed: boolean;
  current?: number;
  limit?: number;
  usage_percent?: number;
  reason?: string;
}

export interface PlanChangePreview {
  current_plan: Plan;
  new_plan: Plan;
  interval: BillingInterval;
  current_price: string;
  new_price: string;
  price_difference: string;
  is_upgrade: boolean;
  proration_amount: string;
}

export interface ChangePlanData {
  plan_id: string;
  interval: BillingInterval;
}

export interface CancelSubscriptionData {
  reason?: string;
}

export interface AddPaymentMethodData {
  card_brand: CardBrand;
  card_last4: string;
  card_exp_month: number;
  card_exp_year: number;
  set_default?: boolean;
}

export interface CreateCheckoutSessionData {
  plan_id: string;
  interval: BillingInterval;
}

export interface CheckoutSessionResponse {
  checkout_url: string;
  session_id: string;
}
