import { useState } from 'react';
import { ArrowUp, ArrowDown, ExternalLink } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import type { Plan, BillingInterval } from '@/types/billing';

interface UpgradeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  plan: Plan | null;
  currentPlanType: string;
  onConfirm: (planId: string, interval: BillingInterval) => void;
  isLoading?: boolean;
  requiresCheckout?: boolean;
}

export function UpgradeDialog({
  open,
  onOpenChange,
  plan,
  currentPlanType,
  onConfirm,
  isLoading,
  requiresCheckout,
}: UpgradeDialogProps) {
  const [annual, setAnnual] = useState(false);

  if (!plan) return null;

  const isUpgrade = plan.sort_order > (['free', 'starter', 'professional', 'business', 'enterprise'].indexOf(currentPlanType));
  const interval: BillingInterval = annual ? 'year' : 'month';
  const price = annual
    ? parseFloat(plan.annual_price)
    : parseFloat(plan.price);
  const monthlyPrice = annual
    ? (parseFloat(plan.annual_price) / 12)
    : parseFloat(plan.price);

  const buttonLabel = isLoading
    ? 'Processing...'
    : requiresCheckout
      ? 'Continue to Payment'
      : `Confirm ${isUpgrade ? 'Upgrade' : 'Downgrade'}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {isUpgrade ? (
              <ArrowUp className="h-5 w-5 text-success" />
            ) : (
              <ArrowDown className="h-5 w-5 text-warning" />
            )}
            {isUpgrade ? 'Upgrade' : 'Downgrade'} to {plan.name}
          </DialogTitle>
          <DialogDescription>
            {isUpgrade
              ? 'Unlock more features and higher limits with this plan.'
              : 'You may lose access to some features with a lower plan.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="flex items-center justify-between p-4 bg-secondary/50 rounded-lg">
            <div>
              <p className="font-semibold text-lg">${monthlyPrice.toFixed(2)}/mo</p>
              {annual && (
                <p className="text-sm text-muted-foreground">
                  ${price.toFixed(2)} billed annually
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="annual-toggle" className="text-sm">Annual billing</Label>
              <Switch
                id="annual-toggle"
                checked={annual}
                onCheckedChange={setAnnual}
              />
            </div>
          </div>

          {annual && (
            <p className="text-sm text-success text-center">
              Save ${((parseFloat(plan.price) * 12) - parseFloat(plan.annual_price)).toFixed(0)}/year with annual billing
            </p>
          )}

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Contacts</span>
              <span>{plan.max_contacts === 999999 ? 'Unlimited' : plan.max_contacts.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Emails/month</span>
              <span>{plan.max_emails_per_month === 999999 ? 'Unlimited' : plan.max_emails_per_month.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Team members</span>
              <span>{plan.max_users === 999 ? 'Unlimited' : plan.max_users}</span>
            </div>
          </div>

          {requiresCheckout && (
            <p className="text-sm text-muted-foreground text-center flex items-center justify-center gap-1">
              <ExternalLink className="h-3 w-3" />
              You'll be redirected to our secure payment page
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => onConfirm(plan.id, interval)}
            disabled={isLoading}
          >
            {buttonLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
