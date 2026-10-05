import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { CreditCard, Lock, ArrowLeft, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { billingApi } from '@/api/billing';
import type { BillingInterval } from '@/types/billing';

export function DemoCheckoutPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [isProcessing, setIsProcessing] = useState(false);

  const planId = searchParams.get('plan_id') || '';
  const planName = searchParams.get('plan_name') || 'Plan';
  const interval = (searchParams.get('interval') || 'month') as BillingInterval;
  const price = searchParams.get('price') || '0.00';

  const displayPrice = interval === 'year'
    ? `$${parseFloat(price).toFixed(2)}/year`
    : `$${parseFloat(price).toFixed(2)}/month`;

  const handlePay = async () => {
    setIsProcessing(true);
    try {
      await billingApi.completeDemoCheckout({
        plan_id: planId,
        interval,
      });
      navigate('/billing?checkout=success', { replace: true });
    } catch {
      setIsProcessing(false);
    }
  };

  const handleCancel = () => {
    navigate('/billing?checkout=cancelled', { replace: true });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Demo banner */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-6 text-center">
          <p className="text-amber-800 text-sm font-medium">
            Demo Mode — Stripe is not configured. This simulates the checkout experience.
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          {/* Header */}
          <div className="bg-slate-900 text-white px-8 py-6">
            <div className="flex items-center justify-between">
              <button
                onClick={handleCancel}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
              <div className="flex items-center gap-2">
                <Lock className="h-4 w-4 text-slate-400" />
                <span className="text-sm text-slate-400">Secure Checkout</span>
              </div>
            </div>
            <div className="mt-6">
              <p className="text-slate-400 text-sm">Subscribe to</p>
              <h1 className="text-2xl font-bold mt-1">{planName}</h1>
              <p className="text-3xl font-bold mt-2">{displayPrice}</p>
            </div>
          </div>

          {/* Form */}
          <div className="px-8 py-6 space-y-5">
            <div>
              <Label htmlFor="email" className="text-sm font-medium text-slate-700">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                defaultValue="demo@example.com"
                className="mt-1.5"
              />
            </div>

            <div>
              <Label htmlFor="card" className="text-sm font-medium text-slate-700">
                Card information
              </Label>
              <div className="mt-1.5 space-y-2">
                <div className="relative">
                  <Input
                    id="card"
                    placeholder="1234 1234 1234 1234"
                    defaultValue="4242 4242 4242 4242"
                    className="pr-16"
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1">
                    <CreditCard className="h-5 w-5 text-slate-400" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input placeholder="MM / YY" defaultValue="12 / 28" />
                  <Input placeholder="CVC" defaultValue="123" />
                </div>
              </div>
            </div>

            <div>
              <Label htmlFor="name" className="text-sm font-medium text-slate-700">
                Name on card
              </Label>
              <Input
                id="name"
                placeholder="Full name"
                defaultValue="Demo User"
                className="mt-1.5"
              />
            </div>

            {/* Order summary */}
            <div className="bg-slate-50 rounded-lg p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">{planName} ({interval === 'year' ? 'Annual' : 'Monthly'})</span>
                <span className="font-medium">{displayPrice}</span>
              </div>
              <div className="border-t pt-2 flex justify-between font-semibold">
                <span>Total due today</span>
                <span>${parseFloat(price).toFixed(2)}</span>
              </div>
            </div>

            <Button
              onClick={handlePay}
              disabled={isProcessing}
              className="w-full h-12 text-base font-semibold"
              size="lg"
            >
              {isProcessing ? (
                'Processing...'
              ) : (
                <span className="flex items-center gap-2">
                  <Check className="h-5 w-5" />
                  Pay {displayPrice}
                </span>
              )}
            </Button>

            <p className="text-xs text-center text-slate-400">
              This is a demo checkout. No real payment will be processed.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
