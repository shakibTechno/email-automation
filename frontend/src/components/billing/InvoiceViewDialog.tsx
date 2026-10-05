import { useRef } from 'react';
import { Printer, X } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import type { Invoice, InvoiceStatus } from '@/types/billing';

interface InvoiceViewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invoice: Invoice | null;
}

const STATUS_COLOR: Record<InvoiceStatus, string> = {
  draft: 'bg-gray-100 text-gray-700',
  open: 'bg-blue-100 text-blue-700',
  paid: 'bg-green-100 text-green-700',
  void: 'bg-red-100 text-red-700',
  uncollectible: 'bg-red-100 text-red-700',
};

export function InvoiceViewDialog({ open, onOpenChange, invoice }: InvoiceViewDialogProps) {
  const printRef = useRef<HTMLDivElement>(null);
  const organization = useAuthStore((s) => s.organization);

  if (!invoice) return null;

  const handlePrint = () => {
    const content = printRef.current;
    if (!content) return;

    const printWindow = window.open('', '_blank', 'width=800,height=900');
    if (!printWindow) return;

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Invoice ${invoice.number || invoice.id}</title>
          <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a1a1a; padding: 40px; }
            .invoice-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 40px; }
            .invoice-title { font-size: 28px; font-weight: 700; color: #111; }
            .invoice-number { font-size: 14px; color: #666; margin-top: 4px; }
            .status-badge { display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase; }
            .status-paid { background: #dcfce7; color: #166534; }
            .status-open { background: #dbeafe; color: #1e40af; }
            .status-draft { background: #f3f4f6; color: #374151; }
            .status-void, .status-uncollectible { background: #fee2e2; color: #991b1b; }
            .parties { display: flex; justify-content: space-between; margin-bottom: 32px; }
            .party { max-width: 45%; }
            .party-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #999; letter-spacing: 0.5px; margin-bottom: 8px; }
            .party-name { font-size: 16px; font-weight: 600; }
            .party-detail { font-size: 13px; color: #555; line-height: 1.6; }
            .dates { display: flex; gap: 40px; margin-bottom: 32px; padding: 16px 0; border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; }
            .date-item label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #999; display: block; margin-bottom: 4px; }
            .date-item span { font-size: 14px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
            th { text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; color: #999; letter-spacing: 0.5px; padding: 12px 16px; border-bottom: 2px solid #e5e7eb; }
            th:last-child { text-align: right; }
            td { padding: 14px 16px; border-bottom: 1px solid #f3f4f6; font-size: 14px; }
            td:last-child { text-align: right; }
            .totals { display: flex; justify-content: flex-end; }
            .totals-table { width: 280px; }
            .totals-row { display: flex; justify-content: space-between; padding: 8px 0; font-size: 14px; }
            .totals-row.total { border-top: 2px solid #111; padding-top: 12px; margin-top: 4px; font-weight: 700; font-size: 16px; }
            .footer { margin-top: 48px; padding-top: 24px; border-top: 1px solid #e5e7eb; text-align: center; font-size: 12px; color: #999; }
            @media print { body { padding: 20px; } }
          </style>
        </head>
        <body>${content.innerHTML}</body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatCurrency = (dollars: string | number) => {
    const num = typeof dollars === 'string' ? parseFloat(dollars) : dollars;
    return `$${num.toFixed(2)}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Invoice {invoice.number || ''}</DialogTitle>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handlePrint}>
                <Printer className="h-4 w-4 mr-2" />
                Print
              </Button>
              <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </DialogHeader>

        <div ref={printRef}>
          {/* Header */}
          <div className="invoice-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 32 }}>
            <div>
              <div className="invoice-title" style={{ fontSize: 28, fontWeight: 700 }}>INVOICE</div>
              <div className="invoice-number" style={{ fontSize: 14, color: '#666', marginTop: 4 }}>
                {invoice.number || `INV-${invoice.id.slice(0, 8).toUpperCase()}`}
              </div>
            </div>
            <span
              className={`status-badge status-${invoice.status}`}
              style={{
                display: 'inline-block',
                padding: '4px 12px',
                borderRadius: 9999,
                fontSize: 12,
                fontWeight: 600,
                textTransform: 'uppercase' as const,
              }}
            >
              <Badge
                variant="outline"
                className={STATUS_COLOR[invoice.status]}
              >
                {invoice.status}
              </Badge>
            </span>
          </div>

          {/* Parties */}
          <div className="parties" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 32 }}>
            <div className="party">
              <div className="party-label" style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const, color: '#999', letterSpacing: 0.5, marginBottom: 8 }}>From</div>
              <div className="party-name" style={{ fontSize: 16, fontWeight: 600 }}>Email Automation Platform</div>
              <div className="party-detail" style={{ fontSize: 13, color: '#555', lineHeight: 1.6 }}>
                Billing Department<br />
                billing@emailautomation.com
              </div>
            </div>
            <div className="party" style={{ textAlign: 'right' }}>
              <div className="party-label" style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const, color: '#999', letterSpacing: 0.5, marginBottom: 8 }}>Bill To</div>
              <div className="party-name" style={{ fontSize: 16, fontWeight: 600 }}>{organization?.name || 'Customer'}</div>
              <div className="party-detail" style={{ fontSize: 13, color: '#555', lineHeight: 1.6 }}>
                {organization?.email || ''}
              </div>
            </div>
          </div>

          {/* Dates */}
          <div className="dates" style={{ display: 'flex', gap: 40, marginBottom: 32, paddingTop: 16, paddingBottom: 16, borderTop: '1px solid #e5e7eb', borderBottom: '1px solid #e5e7eb' }}>
            <div className="date-item">
              <label style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const, color: '#999', display: 'block', marginBottom: 4 }}>Invoice Date</label>
              <span style={{ fontSize: 14 }}>{formatDate(invoice.invoice_date)}</span>
            </div>
            {invoice.paid_at && (
              <div className="date-item">
                <label style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const, color: '#999', display: 'block', marginBottom: 4 }}>Paid On</label>
                <span style={{ fontSize: 14 }}>{formatDate(invoice.paid_at)}</span>
              </div>
            )}
            {invoice.due_date && (
              <div className="date-item">
                <label style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const, color: '#999', display: 'block', marginBottom: 4 }}>Due Date</label>
                <span style={{ fontSize: 14 }}>{formatDate(invoice.due_date)}</span>
              </div>
            )}
          </div>

          {/* Line Items */}
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 24 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const, color: '#999', padding: '12px 16px', borderBottom: '2px solid #e5e7eb' }}>Description</th>
                <th style={{ textAlign: 'center', fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const, color: '#999', padding: '12px 16px', borderBottom: '2px solid #e5e7eb' }}>Qty</th>
                <th style={{ textAlign: 'right', fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const, color: '#999', padding: '12px 16px', borderBottom: '2px solid #e5e7eb' }}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {invoice.line_items.length > 0 ? (
                invoice.line_items.map((item, idx) => (
                  <tr key={idx}>
                    <td style={{ padding: '14px 16px', borderBottom: '1px solid #f3f4f6', fontSize: 14 }}>
                      {item.description}
                      {item.period_start && item.period_end && (
                        <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>
                          {new Date(item.period_start * 1000).toLocaleDateString()} - {new Date(item.period_end * 1000).toLocaleDateString()}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '14px 16px', borderBottom: '1px solid #f3f4f6', fontSize: 14, textAlign: 'center' }}>{item.quantity}</td>
                    <td style={{ padding: '14px 16px', borderBottom: '1px solid #f3f4f6', fontSize: 14, textAlign: 'right' }}>${(item.amount / 100).toFixed(2)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td style={{ padding: '14px 16px', borderBottom: '1px solid #f3f4f6', fontSize: 14 }}>{invoice.description || 'Subscription'}</td>
                  <td style={{ padding: '14px 16px', borderBottom: '1px solid #f3f4f6', fontSize: 14, textAlign: 'center' }}>1</td>
                  <td style={{ padding: '14px 16px', borderBottom: '1px solid #f3f4f6', fontSize: 14, textAlign: 'right' }}>{formatCurrency(invoice.total_dollars)}</td>
                </tr>
              )}
            </tbody>
          </table>

          {/* Totals */}
          <div className="totals" style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <div className="totals-table" style={{ width: 280 }}>
              <div className="totals-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: 14 }}>
                <span style={{ color: '#666' }}>Subtotal</span>
                <span>{formatCurrency(invoice.subtotal_dollars)}</span>
              </div>
              {parseFloat(invoice.tax_dollars) > 0 && (
                <div className="totals-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: 14 }}>
                  <span style={{ color: '#666' }}>Tax</span>
                  <span>{formatCurrency(invoice.tax_dollars)}</span>
                </div>
              )}
              <div className="totals-row total" style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', fontSize: 16, fontWeight: 700, borderTop: '2px solid #111', marginTop: 4 }}>
                <span>Total</span>
                <span>{formatCurrency(invoice.total_dollars)}</span>
              </div>
              {invoice.status === 'paid' && (
                <div className="totals-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: 14 }}>
                  <span style={{ color: '#16a34a', fontWeight: 600 }}>Amount Paid</span>
                  <span style={{ color: '#16a34a', fontWeight: 600 }}>{formatCurrency(invoice.total_dollars)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="footer" style={{ marginTop: 48, paddingTop: 24, borderTop: '1px solid #e5e7eb', textAlign: 'center', fontSize: 12, color: '#999' }}>
            Thank you for your business!
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
