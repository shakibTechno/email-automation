import { AlertTriangle, Clock, CheckCircle2, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Subscription } from '@/types/billing';

interface SubscriptionStatusCardProps {
  subscription: Subscription;
  onReactivate: () => void;
  isReactivating?: boolean;
}

const STATUS_CONFIG: Record<string, {
  label: string;
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  icon: typeof CheckCircle2;
}> = {
  active: { label: 'Active', variant: 'default', icon: CheckCircle2 },
  trialing: { label: 'Trial', variant: 'secondary', icon: Clock },
  past_due: { label: 'Past Due', variant: 'destructive', icon: AlertTriangle },
  cancelled: { label: 'Cancelled', variant: 'destructive', icon: XCircle },
  expired: { label: 'Expired', variant: 'destructive', icon: XCircle },
  incomplete: { label: 'Incomplete', variant: 'outline', icon: AlertTriangle },
};

export function SubscriptionStatusCard({
  subscription,
  onReactivate,
  isReactivating,
}: SubscriptionStatusCardProps) {
  const config = STATUS_CONFIG[subscription.status] || STATUS_CONFIG.active;
  const Icon = config.icon;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Subscription</CardTitle>
          <Badge variant={config.variant} className="flex items-center gap-1">
            <Icon className="h-3 w-3" />
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Plan</span>
          <span className="font-medium">{subscription.plan.name}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Billing</span>
          <span className="font-medium capitalize">{subscription.interval}ly</span>
        </div>

        {subscription.is_trialing && subscription.trial_days_remaining > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Trial ends in</span>
            <span className="font-medium text-yellow-600">
              {subscription.trial_days_remaining} days
            </span>
          </div>
        )}

        {subscription.current_period_end && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              {subscription.cancel_at_period_end ? 'Cancels on' : 'Next billing'}
            </span>
            <span className="font-medium">
              {new Date(subscription.current_period_end).toLocaleDateString()}
            </span>
          </div>
        )}

        {subscription.cancel_at_period_end && (
          <div className="rounded-md bg-yellow-50 border border-yellow-200 p-3 mt-2">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-yellow-800">
                  Cancellation scheduled
                </p>
                <p className="text-xs text-yellow-700 mt-1">
                  Your subscription will be cancelled at the end of the current billing period.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={onReactivate}
                  disabled={isReactivating}
                >
                  {isReactivating ? 'Reactivating...' : 'Reactivate Subscription'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
