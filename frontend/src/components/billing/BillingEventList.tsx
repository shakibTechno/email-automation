import {
  CreditCard,
  ArrowUpCircle,
  ArrowDownCircle,
  XCircle,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Receipt,
} from 'lucide-react';
import type { BillingEvent } from '@/types/billing';

interface BillingEventListProps {
  events: BillingEvent[];
}

const EVENT_ICONS: Record<string, typeof CreditCard> = {
  subscription_created: CheckCircle2,
  subscription_updated: ArrowUpCircle,
  subscription_cancelled: XCircle,
  plan_upgraded: ArrowUpCircle,
  plan_downgraded: ArrowDownCircle,
  payment_succeeded: CheckCircle2,
  payment_failed: AlertTriangle,
  invoice_created: Receipt,
  invoice_paid: Receipt,
  trial_started: Clock,
  trial_ending: AlertTriangle,
  trial_expired: XCircle,
  payment_method_added: CreditCard,
  payment_method_removed: CreditCard,
};

const EVENT_COLORS: Record<string, string> = {
  payment_succeeded: 'text-green-500',
  payment_failed: 'text-red-500',
  subscription_cancelled: 'text-red-500',
  trial_expired: 'text-red-500',
  plan_upgraded: 'text-green-500',
  plan_downgraded: 'text-yellow-500',
  trial_ending: 'text-yellow-500',
  invoice_paid: 'text-green-500',
};

export function BillingEventList({ events }: BillingEventListProps) {
  if (events.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No billing events yet
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => {
        const Icon = EVENT_ICONS[event.event_type] || CreditCard;
        const color = EVENT_COLORS[event.event_type] || 'text-gray-500';

        return (
          <div key={event.id} className="flex items-start gap-3 py-2">
            <div className={`mt-0.5 ${color}`}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm">{event.description}</p>
              <p className="text-xs text-muted-foreground">
                {new Date(event.created_at).toLocaleString()}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
