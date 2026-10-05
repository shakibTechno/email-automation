import { useState } from 'react';
import { Eye, Download, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { InvoiceViewDialog } from './InvoiceViewDialog';
import type { Invoice, InvoiceStatus } from '@/types/billing';

interface InvoiceTableProps {
  invoices: Invoice[];
}

const STATUS_VARIANT: Record<InvoiceStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  draft: 'outline',
  open: 'secondary',
  paid: 'default',
  void: 'destructive',
  uncollectible: 'destructive',
};

export function InvoiceTable({ invoices }: InvoiceTableProps) {
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [showView, setShowView] = useState(false);

  if (invoices.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No invoices yet
      </div>
    );
  }

  const handleView = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
    setShowView(true);
  };

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Invoice</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {invoices.map((invoice) => (
            <TableRow key={invoice.id}>
              <TableCell className="font-medium">
                {invoice.number || 'Draft'}
              </TableCell>
              <TableCell>
                {invoice.invoice_date
                  ? new Date(invoice.invoice_date).toLocaleDateString()
                  : '-'}
              </TableCell>
              <TableCell>
                ${invoice.total_dollars}
                <span className="text-muted-foreground text-xs ml-1 uppercase">
                  {invoice.currency}
                </span>
              </TableCell>
              <TableCell>
                <Badge variant={STATUS_VARIANT[invoice.status] || 'outline'}>
                  {invoice.status}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleView(invoice)}
                    title="View Invoice"
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  {invoice.stripe_invoice_pdf && (
                    <Button
                      variant="ghost"
                      size="icon"
                      asChild
                    >
                      <a
                        href={invoice.stripe_invoice_pdf}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Download PDF"
                      >
                        <Download className="h-4 w-4" />
                      </a>
                    </Button>
                  )}
                  {invoice.stripe_hosted_invoice_url && (
                    <Button
                      variant="ghost"
                      size="icon"
                      asChild
                    >
                      <a
                        href={invoice.stripe_hosted_invoice_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="View on Stripe"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <InvoiceViewDialog
        open={showView}
        onOpenChange={setShowView}
        invoice={selectedInvoice}
      />
    </>
  );
}
