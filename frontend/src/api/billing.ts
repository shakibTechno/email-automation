import { apiClient } from './client';
import type {
  Plan,
  Subscription,
  PaymentMethod,
  Invoice,
  BillingEvent,
  BillingOverview,
  UsageLimit,
  PlanChangePreview,
  ChangePlanData,
  CancelSubscriptionData,
  CreateCheckoutSessionData,
  CheckoutSessionResponse,
  AddPaymentMethodData,
} from '@/types/billing';

const BASE = '/billing';

export const billingApi = {
  // Plans
  getPlans: async (): Promise<Plan[]> => {
    const { data } = await apiClient.get(`${BASE}/plans`);
    return data;
  },

  // Overview
  getOverview: async (): Promise<BillingOverview> => {
    const { data } = await apiClient.get(`${BASE}/overview`);
    return data;
  },

  // Subscription
  getSubscription: async (): Promise<Subscription> => {
    const { data } = await apiClient.get(`${BASE}/subscription`);
    return data;
  },

  changePlan: async (payload: ChangePlanData): Promise<Subscription> => {
    const { data } = await apiClient.post(`${BASE}/change-plan`, payload);
    return data;
  },

  createCheckoutSession: async (payload: CreateCheckoutSessionData): Promise<CheckoutSessionResponse> => {
    const { data } = await apiClient.post(`${BASE}/create-checkout-session`, payload);
    return data;
  },

  completeDemoCheckout: async (payload: CreateCheckoutSessionData): Promise<Subscription> => {
    const { data } = await apiClient.post(`${BASE}/complete-demo-checkout`, payload);
    return data;
  },

  previewPlanChange: async (payload: ChangePlanData): Promise<PlanChangePreview> => {
    const { data } = await apiClient.post(`${BASE}/preview-change`, payload);
    return data;
  },

  cancelSubscription: async (payload: CancelSubscriptionData): Promise<Subscription> => {
    const { data } = await apiClient.post(`${BASE}/cancel`, payload);
    return data;
  },

  reactivateSubscription: async (): Promise<Subscription> => {
    const { data } = await apiClient.post(`${BASE}/reactivate`);
    return data;
  },

  // Payment Methods
  getPaymentMethods: async (): Promise<PaymentMethod[]> => {
    const { data } = await apiClient.get(`${BASE}/payment-methods`);
    return data;
  },

  deletePaymentMethod: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE}/payment-methods/${id}`);
  },

  setDefaultPaymentMethod: async (id: string): Promise<PaymentMethod> => {
    const { data } = await apiClient.post(`${BASE}/payment-methods/${id}/set-default`);
    return data;
  },

  createSetupIntent: async (): Promise<{ client_secret: string }> => {
    const { data } = await apiClient.post(`${BASE}/setup-intent`);
    return data;
  },

  addPaymentMethod: async (payload: AddPaymentMethodData): Promise<PaymentMethod> => {
    const { data } = await apiClient.post(`${BASE}/add-payment-method`, payload);
    return data;
  },

  // Invoices
  getInvoices: async (): Promise<Invoice[]> => {
    const { data } = await apiClient.get(`${BASE}/invoices`);
    return data;
  },

  // Events
  getEvents: async (): Promise<BillingEvent[]> => {
    const { data } = await apiClient.get(`${BASE}/events`);
    return data;
  },

  // Usage
  checkUsage: async (type: string): Promise<UsageLimit> => {
    const { data } = await apiClient.get(`${BASE}/usage`, { params: { type } });
    return data;
  },

  // Stripe config
  getStripeConfig: async (): Promise<{ public_key: string }> => {
    const { data } = await apiClient.get(`${BASE}/stripe-config`);
    return data;
  },
};
