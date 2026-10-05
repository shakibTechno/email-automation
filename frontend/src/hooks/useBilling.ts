import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { billingApi } from '@/api/billing';
import { toast } from 'sonner';
import type { ChangePlanData, CancelSubscriptionData, CreateCheckoutSessionData, AddPaymentMethodData } from '@/types/billing';

const BILLING_KEYS = {
  all: ['billing'] as const,
  overview: () => [...BILLING_KEYS.all, 'overview'] as const,
  subscription: () => [...BILLING_KEYS.all, 'subscription'] as const,
  plans: () => [...BILLING_KEYS.all, 'plans'] as const,
  paymentMethods: () => [...BILLING_KEYS.all, 'payment-methods'] as const,
  invoices: () => [...BILLING_KEYS.all, 'invoices'] as const,
  events: () => [...BILLING_KEYS.all, 'events'] as const,
  usage: (type: string) => [...BILLING_KEYS.all, 'usage', type] as const,
  stripeConfig: () => [...BILLING_KEYS.all, 'stripe-config'] as const,
};

export function usePlans() {
  return useQuery({
    queryKey: BILLING_KEYS.plans(),
    queryFn: billingApi.getPlans,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useBillingOverview() {
  return useQuery({
    queryKey: BILLING_KEYS.overview(),
    queryFn: billingApi.getOverview,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useSubscription() {
  return useQuery({
    queryKey: BILLING_KEYS.subscription(),
    queryFn: billingApi.getSubscription,
    staleTime: 2 * 60 * 1000,
  });
}

export function usePaymentMethods() {
  return useQuery({
    queryKey: BILLING_KEYS.paymentMethods(),
    queryFn: billingApi.getPaymentMethods,
    staleTime: 5 * 60 * 1000,
  });
}

export function useInvoices() {
  return useQuery({
    queryKey: BILLING_KEYS.invoices(),
    queryFn: billingApi.getInvoices,
    staleTime: 5 * 60 * 1000,
  });
}

export function useBillingEvents() {
  return useQuery({
    queryKey: BILLING_KEYS.events(),
    queryFn: billingApi.getEvents,
    staleTime: 2 * 60 * 1000,
  });
}

export function useUsageLimit(type: string) {
  return useQuery({
    queryKey: BILLING_KEYS.usage(type),
    queryFn: () => billingApi.checkUsage(type),
    staleTime: 60 * 1000, // 1 minute
  });
}

export function useStripeConfig() {
  return useQuery({
    queryKey: BILLING_KEYS.stripeConfig(),
    queryFn: billingApi.getStripeConfig,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

export function useBillingMutations() {
  const queryClient = useQueryClient();

  const invalidateBilling = () => {
    queryClient.invalidateQueries({ queryKey: BILLING_KEYS.all });
  };

  const changePlanMutation = useMutation({
    mutationFn: (data: ChangePlanData) => billingApi.changePlan(data),
    onSuccess: () => {
      toast.success('Plan changed successfully');
      invalidateBilling();
    },
    onError: () => {
      toast.error('Failed to change plan');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (data: CancelSubscriptionData) => billingApi.cancelSubscription(data),
    onSuccess: () => {
      toast.success('Subscription will be cancelled at the end of the billing period');
      invalidateBilling();
    },
    onError: () => {
      toast.error('Failed to cancel subscription');
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: () => billingApi.reactivateSubscription(),
    onSuccess: () => {
      toast.success('Subscription reactivated');
      invalidateBilling();
    },
    onError: () => {
      toast.error('Failed to reactivate subscription');
    },
  });

  const deletePaymentMethodMutation = useMutation({
    mutationFn: (id: string) => billingApi.deletePaymentMethod(id),
    onSuccess: () => {
      toast.success('Payment method removed');
      queryClient.invalidateQueries({ queryKey: BILLING_KEYS.paymentMethods() });
    },
    onError: () => {
      toast.error('Failed to remove payment method');
    },
  });

  const createCheckoutSessionMutation = useMutation({
    mutationFn: (data: CreateCheckoutSessionData) => billingApi.createCheckoutSession(data),
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
    onError: () => {
      toast.error('Failed to start checkout');
    },
  });

  const setDefaultPaymentMethodMutation = useMutation({
    mutationFn: (id: string) => billingApi.setDefaultPaymentMethod(id),
    onSuccess: () => {
      toast.success('Default payment method updated');
      queryClient.invalidateQueries({ queryKey: BILLING_KEYS.paymentMethods() });
    },
    onError: () => {
      toast.error('Failed to set default payment method');
    },
  });

  const addPaymentMethodMutation = useMutation({
    mutationFn: (data: AddPaymentMethodData) => billingApi.addPaymentMethod(data),
    onSuccess: () => {
      toast.success('Payment method added');
      queryClient.invalidateQueries({ queryKey: BILLING_KEYS.paymentMethods() });
    },
    onError: () => {
      toast.error('Failed to add payment method');
    },
  });

  return {
    changePlan: changePlanMutation,
    createCheckoutSession: createCheckoutSessionMutation,
    cancel: cancelMutation,
    reactivate: reactivateMutation,
    deletePaymentMethod: deletePaymentMethodMutation,
    setDefaultPaymentMethod: setDefaultPaymentMethodMutation,
    addPaymentMethod: addPaymentMethodMutation,
  };
}
