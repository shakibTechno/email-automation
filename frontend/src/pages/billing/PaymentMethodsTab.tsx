import { useState } from 'react';
import { Loader2, Plus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { usePaymentMethods, useBillingMutations } from '@/hooks/useBilling';
import { PaymentMethodCard } from '@/components/billing/PaymentMethodCard';
import { AddPaymentMethodDialog } from '@/components/billing/AddPaymentMethodDialog';

export function PaymentMethodsTab() {
  const { data: methods, isLoading } = usePaymentMethods();
  const { deletePaymentMethod, setDefaultPaymentMethod, addPaymentMethod } = useBillingMutations();
  const [showAdd, setShowAdd] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Payment Methods</CardTitle>
            <Button
              size="sm"
              className="flex items-center gap-2"
              onClick={() => setShowAdd(true)}
            >
              <Plus className="h-4 w-4" />
              Add Payment Method
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!methods || methods.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No payment methods on file.</p>
              <p className="text-sm mt-1">
                Add a payment method to subscribe to a paid plan.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {methods.map((method) => (
                <PaymentMethodCard
                  key={method.id}
                  method={method}
                  onDelete={(id) => deletePaymentMethod.mutate(id)}
                  onSetDefault={(id) => setDefaultPaymentMethod.mutate(id)}
                  isDeleting={deletePaymentMethod.isPending}
                  isSettingDefault={setDefaultPaymentMethod.isPending}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <AddPaymentMethodDialog
        open={showAdd}
        onOpenChange={setShowAdd}
        onSubmit={(data) => {
          addPaymentMethod.mutate(data, {
            onSuccess: () => setShowAdd(false),
          });
        }}
        isLoading={addPaymentMethod.isPending}
      />
    </div>
  );
}
