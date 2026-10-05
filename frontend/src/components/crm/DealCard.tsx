import { useNavigate } from 'react-router-dom';
import { Calendar, MessageSquare, AlertTriangle } from 'lucide-react';
import { DealKanbanCard } from '@/types/crm';
import { PriorityBadge } from './PriorityBadge';
import { cn } from '@/lib/utils';

interface DealCardProps {
  deal: DealKanbanCard;
}

const formatCurrency = (value: number, currency: string) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

export const DealCard = ({ deal }: DealCardProps) => {
  const navigate = useNavigate();

  const isOverdue =
    deal.close_date &&
    new Date(deal.close_date) < new Date() &&
    deal.status === 'open';

  return (
    <div
      className={cn(
        "bg-white rounded-lg border p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer",
        deal.is_rotting ? "border-orange-300 bg-orange-50/40" : "border-gray-200"
      )}
      onClick={() => navigate(`/crm/deals/${deal.id}`)}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="text-sm font-medium text-gray-900 line-clamp-2 flex-1">
          {deal.title}
        </h4>
        <div className="flex items-center gap-1 shrink-0">
          {deal.is_rotting && (
            <span title={`No activity for ${deal.days_since_activity} days`}>
              <AlertTriangle className="h-3.5 w-3.5 text-orange-500" />
            </span>
          )}
          <PriorityBadge priority={deal.priority} dotOnly />
        </div>
      </div>

      {deal.value > 0 && (
        <div className="text-sm font-semibold text-gray-900 mb-2">
          {formatCurrency(deal.value, deal.currency)}
        </div>
      )}

      {deal.primary_contact_name && (
        <div className="text-xs text-muted-foreground mb-1 truncate">
          {deal.primary_contact_name}
        </div>
      )}

      {deal.is_rotting && deal.days_since_activity !== null && (
        <div className="text-xs text-orange-600 font-medium mb-2">
          No activity for {deal.days_since_activity}d
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        {deal.close_date && (
          <div className={cn('flex items-center gap-1', isOverdue && 'text-red-500')}>
            <Calendar className="h-3 w-3" />
            <span>{new Date(deal.close_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
          </div>
        )}

        {deal.activity_count > 0 && (
          <div className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            <span>{deal.activity_count}</span>
          </div>
        )}
      </div>
    </div>
  );
};
