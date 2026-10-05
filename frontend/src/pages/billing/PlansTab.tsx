import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { usePlans, useSubscription, useBillingMutations } from '@/hooks/useBilling';
import { PlanCard } from '@/components/billing/PlanCard';
import { UpgradeDialog } from '@/components/billing/UpgradeDialog';
import { CancelDialog } from '@/components/billing/CancelDialog';
import { Button } from '@/components/ui/button';
import type { Plan, BillingInterval } from '@/types/billing';

export function PlansTab() {
  const { data: plans, isLoading: plansLoading } = usePlans();
  const { data: subscription, isLoading: subLoading } = useSubscription();
  const { changePlan, createCheckoutSession, cancel } = useBillingMutations();

  const [annual, setAnnual] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [showCancel, setShowCancel] = useState(false);

  if (plansLoading || subLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Filter to monthly plans only (we show pricing toggle for annual)
  const monthlyPlans = plans?.filter((p) => p.interval === 'month') || [];
  const currentPlanType = subscription?.plan?.plan_type || 'free';

  // Checkout is required when there's no existing Stripe subscription
  const needsCheckout = !subscription?.has_stripe_subscription;

  const handleSelectPlan = (plan: Plan) => {
    setSelectedPlan(plan);
    setShowUpgrade(true);
  };

  const handleConfirmChange = (planId: string, interval: BillingInterval) => {
    // If no existing Stripe subscription and the selected plan is paid, redirect to checkout
    if (needsCheckout && selectedPlan?.plan_type !== 'free') {
      createCheckoutSession.mutate(
        { plan_id: planId, interval },
        {
          onSuccess: () => {
            // Redirect happens in the mutation onSuccess (window.location.href)
          },
        },
      );
    } else {
      changePlan.mutate(
        { plan_id: planId, interval },
        {
          onSuccess: () => {
            setShowUpgrade(false);
            setSelectedPlan(null);
          },
        },
      );
    }
  };

  const handleConfirmCancel = (reason: string) => {
    cancel.mutate(
      { reason },
      { onSuccess: () => setShowCancel(false) },
    );
  };

  const isProcessing = changePlan.isPending || createCheckoutSession.isPending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Choose a Plan</h2>
          <p className="text-sm text-muted-foreground">
            Select the plan that best fits your needs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Label htmlFor="billing-toggle" className="text-sm">Monthly</Label>
          <Switch
            id="billing-toggle"
            checked={annual}
            onCheckedChange={setAnnual}
          />
          <Label htmlFor="billing-toggle" className="text-sm">
            Annual <span className="text-success font-medium">(Save ~17%)</span>
          </Label>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {monthlyPlans.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            interval={annual ? 'year' : 'month'}
            isCurrentPlan={plan.plan_type === currentPlanType}
            onSelect={handleSelectPlan}
            isLoading={isProcessing}
          />
        ))}
      </div>

      {subscription && !subscription.is_on_free_plan && !subscription.cancel_at_period_end && (
        <div className="text-center pt-4 border-t">
          <Button
            variant="ghost"
            className="text-destructive hover:text-destructive"
            onClick={() => setShowCancel(true)}
          >
            Cancel Subscription
          </Button>
        </div>
      )}

      <UpgradeDialog
        open={showUpgrade}
        onOpenChange={setShowUpgrade}
        plan={selectedPlan}
        currentPlanType={currentPlanType}
        onConfirm={handleConfirmChange}
        isLoading={isProcessing}
        requiresCheckout={needsCheckout && selectedPlan?.plan_type !== 'free'}
      />

      <CancelDialog
        open={showCancel}
        onOpenChange={setShowCancel}
        periodEnd={subscription?.current_period_end || null}
        onConfirm={handleConfirmCancel}
        isLoading={cancel.isPending}
      />
    </div>
  );
}
