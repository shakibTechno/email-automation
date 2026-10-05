import { Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useInvoices } from '@/hooks/useBilling';
import { InvoiceTable } from '@/components/billing/InvoiceTable';

export function InvoicesTab() {
  const { data: invoices, isLoading } = useInvoices();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Invoice History</CardTitle>
      </CardHeader>
      <CardContent>
        <InvoiceTable invoices={invoices || []} />
      </CardContent>
    </Card>
  );
}
