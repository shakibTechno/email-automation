import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

interface CancelDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  periodEnd: string | null;
  onConfirm: (reason: string) => void;
  isLoading?: boolean;
}

export function CancelDialog({
  open,
  onOpenChange,
  periodEnd,
  onConfirm,
  isLoading,
}: CancelDialogProps) {
  const [reason, setReason] = useState('');

  const handleConfirm = () => {
    onConfirm(reason);
    setReason('');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            Cancel Subscription
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to cancel your subscription?
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="rounded-md bg-yellow-50 border border-yellow-200 p-4">
            <ul className="text-sm text-yellow-800 space-y-1 list-disc list-inside">
              <li>Your subscription will remain active until the end of the current billing period</li>
              {periodEnd && (
                <li>Access expires on {new Date(periodEnd).toLocaleDateString()}</li>
              )}
              <li>You will be downgraded to the Free plan after cancellation</li>
              <li>You can reactivate your subscription at any time before the period ends</li>
            </ul>
          </div>

          <div className="space-y-2">
            <Label htmlFor="cancel-reason">
              Help us improve — why are you cancelling? (optional)
            </Label>
            <Textarea
              id="cancel-reason"
              placeholder="Tell us why you're leaving..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Keep Subscription
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={isLoading}
          >
            {isLoading ? 'Cancelling...' : 'Cancel Subscription'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
