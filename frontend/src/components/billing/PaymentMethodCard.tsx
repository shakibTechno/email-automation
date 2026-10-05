import { CreditCard, Trash2, Star } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { PaymentMethod } from '@/types/billing';

interface PaymentMethodCardProps {
  method: PaymentMethod;
  onDelete: (id: string) => void;
  onSetDefault: (id: string) => void;
  isDeleting?: boolean;
  isSettingDefault?: boolean;
}

const BRAND_DISPLAY: Record<string, string> = {
  visa: 'Visa',
  mastercard: 'Mastercard',
  amex: 'Amex',
  discover: 'Discover',
  other: 'Card',
};

export function PaymentMethodCard({
  method,
  onDelete,
  onSetDefault,
  isDeleting,
  isSettingDefault,
}: PaymentMethodCardProps) {
  return (
    <Card className={cn(
      method.is_default && 'border-primary',
      method.is_expired && 'border-red-300 bg-red-50/50',
    )}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-gray-100 flex items-center justify-center">
              <CreditCard className="h-5 w-5 text-gray-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">
                  {BRAND_DISPLAY[method.card_brand] || 'Card'} ****{method.card_last4}
                </span>
                {method.is_default && (
                  <Badge variant="secondary" className="text-xs">
                    <Star className="h-3 w-3 mr-1" />
                    Default
                  </Badge>
                )}
                {method.is_expired && (
                  <Badge variant="destructive" className="text-xs">
                    Expired
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                Expires {String(method.card_exp_month).padStart(2, '0')}/{method.card_exp_year}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {!method.is_default && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onSetDefault(method.id)}
                disabled={isSettingDefault}
              >
                Set Default
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(method.id)}
              disabled={isDeleting}
              className="text-red-500 hover:text-red-700"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
