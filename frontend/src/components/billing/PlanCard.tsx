import { Check, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Plan, BillingInterval } from '@/types/billing';

interface PlanCardProps {
  plan: Plan;
  interval: BillingInterval;
  isCurrentPlan: boolean;
  onSelect: (plan: Plan) => void;
  isLoading?: boolean;
}

const FEATURES_BY_PLAN: Record<string, string[]> = {
  free: [
    'Up to 500 contacts',
    '1,000 emails/month',
    'Basic email templates',
    'Email support',
  ],
  starter: [
    'Up to 2,500 contacts',
    '25,000 emails/month',
    'All email templates',
    '5 active automations',
    '5 landing pages',
    'Forms and popups',
    'Basic reporting',
    'No watermark',
  ],
  professional: [
    'Up to 10,000 contacts',
    '100,000 emails/month',
    'Unlimited automations',
    'Unlimited landing pages',
    'A/B testing',
    'Advanced segmentation',
    'Lead scoring',
    'SMS marketing',
    'Custom reports',
    'Priority support',
  ],
  business: [
    'Up to 50,000 contacts',
    '500,000 emails/month',
    'All Professional features',
    'CRM & pipeline',
    'AI-powered features',
    'Up to 10 users',
    'Advanced analytics',
    'API access',
    'Dedicated account manager',
  ],
  enterprise: [
    'Unlimited contacts',
    'Custom email volume',
    'All Business features',
    'Dedicated IP address',
    'SSO (SAML)',
    'White-labeling',
    'Priority SLA support',
    'Custom integrations',
  ],
};

export function PlanCard({ plan, interval, isCurrentPlan, onSelect, isLoading }: PlanCardProps) {
  const price = interval === 'year'
    ? (parseFloat(plan.annual_price) / 12).toFixed(0)
    : parseFloat(plan.price).toFixed(0);

  const isEnterprise = plan.plan_type === 'enterprise';
  const features = FEATURES_BY_PLAN[plan.plan_type] || [];

  return (
    <Card className={cn(
      'relative flex flex-col',
      plan.is_popular && 'border-primary shadow-lg ring-1 ring-primary',
      isCurrentPlan && 'border-success bg-success/[.10]/50'
    )}>
      {plan.is_popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <Badge className="bg-primary text-white flex items-center gap-1">
            <Star className="h-3 w-3" />
            Most Popular
          </Badge>
        </div>
      )}

      <CardHeader className="text-center pb-2">
        <h3 className="text-lg font-semibold">{plan.name}</h3>
        <div className="mt-2">
          {isEnterprise ? (
            <div className="text-3xl font-bold">Custom</div>
          ) : plan.plan_type === 'free' ? (
            <div className="text-3xl font-bold">$0</div>
          ) : (
            <div>
              <span className="text-3xl font-bold">${price}</span>
              <span className="text-muted-foreground text-sm">/mo</span>
              {interval === 'year' && (
                <p className="text-xs text-muted-foreground mt-1">
                  Billed annually (${parseFloat(plan.annual_price).toFixed(0)}/yr)
                </p>
              )}
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1">
        <ul className="space-y-2">
          {features.map((feature) => (
            <li key={feature} className="flex items-start gap-2 text-sm">
              <Check className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
              <span>{feature}</span>
            </li>
          ))}
        </ul>
      </CardContent>

      <CardFooter>
        {isCurrentPlan ? (
          <Button variant="outline" className="w-full" disabled>
            Current Plan
          </Button>
        ) : isEnterprise ? (
          <Button variant="outline" className="w-full">
            Contact Sales
          </Button>
        ) : (
          <Button
            className="w-full"
            variant={plan.is_popular ? 'default' : 'outline'}
            onClick={() => onSelect(plan)}
            disabled={isLoading}
          >
            {isLoading ? 'Processing...' : 'Select Plan'}
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
