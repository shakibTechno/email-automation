import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { useBillingOverview, useBillingEvents, useBillingMutations } from '@/hooks/useBilling';
import { SubscriptionStatusCard } from '@/components/billing/SubscriptionStatusCard';
import { UsageBar } from '@/components/billing/UsageBar';
import { BillingEventList } from '@/components/billing/BillingEventList';

export function BillingOverviewTab() {
  const { data: overview, isLoading } = useBillingOverview();
  const { data: events } = useBillingEvents();
  const { reactivate } = useBillingMutations();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No billing information available.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        <SubscriptionStatusCard
          subscription={overview.subscription}
          onReactivate={() => reactivate.mutate()}
          isReactivating={reactivate.isPending}
        />

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Current Plan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{overview.plan.name}</span>
              {parseFloat(overview.plan.price) > 0 && (
                <span className="text-lg font-semibold">
                  ${parseFloat(overview.plan.price).toFixed(0)}/mo
                </span>
              )}
            </div>
            {overview.is_trialing && overview.trial_days_remaining > 0 && (
              <p className="text-sm text-warning">
                Trial: {overview.trial_days_remaining} days remaining
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Usage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <UsageBar
            label="Contacts"
            current={overview.contact_count}
            limit={overview.contacts_limit}
          />
          <UsageBar
            label="Emails this month"
            current={overview.emails_sent}
            limit={overview.emails_limit}
          />
        </CardContent>
      </Card>

      {events && events.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <BillingEventList events={events.slice(0, 10)} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
