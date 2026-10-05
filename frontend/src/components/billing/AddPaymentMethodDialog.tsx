import { useState } from 'react';
import { CreditCard } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { CardBrand } from '@/types/billing';

interface AddPaymentMethodDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: {
    card_brand: CardBrand;
    card_last4: string;
    card_exp_month: number;
    card_exp_year: number;
    set_default: boolean;
  }) => void;
  isLoading?: boolean;
}

export function AddPaymentMethodDialog({
  open,
  onOpenChange,
  onSubmit,
  isLoading,
}: AddPaymentMethodDialogProps) {
  const [cardNumber, setCardNumber] = useState('');
  const [expMonth, setExpMonth] = useState('');
  const [expYear, setExpYear] = useState('');
  const [brand, setBrand] = useState<CardBrand>('visa');
  const [cvc, setCvc] = useState('');

  const formatCardNumber = (value: string) => {
    const digits = value.replace(/\D/g, '').slice(0, 16);
    return digits.replace(/(\d{4})(?=\d)/g, '$1 ');
  };

  const detectBrand = (number: string): CardBrand => {
    const digits = number.replace(/\s/g, '');
    if (/^4/.test(digits)) return 'visa';
    if (/^5[1-5]/.test(digits)) return 'mastercard';
    if (/^3[47]/.test(digits)) return 'amex';
    if (/^6(?:011|5)/.test(digits)) return 'discover';
    return brand;
  };

  const handleCardNumberChange = (value: string) => {
    const formatted = formatCardNumber(value);
    setCardNumber(formatted);
    setBrand(detectBrand(formatted));
  };

  const handleSubmit = () => {
    const digits = cardNumber.replace(/\s/g, '');
    const last4 = digits.slice(-4);
    if (last4.length !== 4 || !expMonth || !expYear) return;

    onSubmit({
      card_brand: brand,
      card_last4: last4,
      card_exp_month: parseInt(expMonth),
      card_exp_year: parseInt(expYear),
      set_default: true,
    });
  };

  const handleOpenChange = (value: boolean) => {
    if (!value) {
      setCardNumber('');
      setExpMonth('');
      setExpYear('');
      setCvc('');
      setBrand('visa');
    }
    onOpenChange(value);
  };

  const digits = cardNumber.replace(/\s/g, '');
  const isValid = digits.length >= 13 && expMonth && expYear && cvc.length >= 3;

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 12 }, (_, i) => currentYear + i);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Add Payment Method
          </DialogTitle>
          <DialogDescription>
            Enter your card details below.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <Label htmlFor="card-number">Card Number</Label>
            <div className="relative mt-1.5">
              <Input
                id="card-number"
                placeholder="1234 5678 9012 3456"
                value={cardNumber}
                onChange={(e) => handleCardNumberChange(e.target.value)}
                maxLength={19}
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <Select value={brand} onValueChange={(v) => setBrand(v as CardBrand)}>
                  <SelectTrigger className="h-7 w-[110px] text-xs border-0 shadow-none bg-transparent focus:ring-0">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="visa">Visa</SelectItem>
                    <SelectItem value="mastercard">Mastercard</SelectItem>
                    <SelectItem value="amex">Amex</SelectItem>
                    <SelectItem value="discover">Discover</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label htmlFor="exp-month">Month</Label>
              <Select value={expMonth} onValueChange={setExpMonth}>
                <SelectTrigger id="exp-month" className="mt-1.5">
                  <SelectValue placeholder="MM" />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                    <SelectItem key={m} value={String(m)}>
                      {String(m).padStart(2, '0')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="exp-year">Year</Label>
              <Select value={expYear} onValueChange={setExpYear}>
                <SelectTrigger id="exp-year" className="mt-1.5">
                  <SelectValue placeholder="YYYY" />
                </SelectTrigger>
                <SelectContent>
                  {years.map((y) => (
                    <SelectItem key={y} value={String(y)}>
                      {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="cvc">CVC</Label>
              <Input
                id="cvc"
                placeholder="123"
                value={cvc}
                onChange={(e) => setCvc(e.target.value.replace(/\D/g, '').slice(0, 4))}
                maxLength={4}
                className="mt-1.5"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isValid || isLoading}>
            {isLoading ? 'Adding...' : 'Add Card'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
