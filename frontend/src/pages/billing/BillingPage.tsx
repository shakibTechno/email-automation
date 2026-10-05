import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CreditCard, Receipt, BarChart3, History } from 'lucide-react';
import { toast } from 'sonner';
import { BillingOverviewTab } from './BillingOverviewTab';
import { PlansTab } from './PlansTab';
import { InvoicesTab } from './InvoicesTab';
import { PaymentMethodsTab } from './PaymentMethodsTab';

export function BillingPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  // Handle checkout return
  useEffect(() => {
    const checkoutStatus = searchParams.get('checkout');
    if (checkoutStatus === 'success') {
      toast.success('Payment successful! Your plan has been updated.');
      queryClient.invalidateQueries({ queryKey: ['billing'] });
      setSearchParams({}, { replace: true });
    } else if (checkoutStatus === 'cancelled') {
      toast.info('Checkout cancelled. Your plan has not been changed.');
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams, queryClient]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
        <p className="text-muted-foreground">
          Manage your subscription, payment methods, and invoices.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="plans" className="flex items-center gap-2">
            <Receipt className="h-4 w-4" />
            Plans
          </TabsTrigger>
          <TabsTrigger value="invoices" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            Invoices
          </TabsTrigger>
          <TabsTrigger value="payment" className="flex items-center gap-2">
            <CreditCard className="h-4 w-4" />
            Payment
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <BillingOverviewTab />
        </TabsContent>
        <TabsContent value="plans" className="mt-6">
          <PlansTab />
        </TabsContent>
        <TabsContent value="invoices" className="mt-6">
          <InvoicesTab />
        </TabsContent>
        <TabsContent value="payment" className="mt-6">
          <PaymentMethodsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
