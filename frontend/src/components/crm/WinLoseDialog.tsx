import { useState } from 'react';
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

interface WinLoseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  type: 'win' | 'lose';
  dealTitle: string;
  onConfirm: (reason: string) => void;
  isLoading?: boolean;
}

export const WinLoseDialog = ({
  open,
  onOpenChange,
  type,
  dealTitle,
  onConfirm,
  isLoading,
}: WinLoseDialogProps) => {
  const [reason, setReason] = useState('');

  const handleConfirm = () => {
    onConfirm(reason);
    setReason('');
  };

  const isWin = type === 'win';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isWin ? 'Mark Deal as Won' : 'Mark Deal as Lost'}
          </DialogTitle>
          <DialogDescription>
            {isWin
              ? `Are you sure you want to mark "${dealTitle}" as won?`
              : `Are you sure you want to mark "${dealTitle}" as lost?`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <Label htmlFor="reason">
            {isWin ? 'Win Reason (optional)' : 'Loss Reason (optional)'}
          </Label>
          <Textarea
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={
              isWin
                ? 'e.g. Competitive pricing, great relationship...'
                : 'e.g. Budget constraints, chose competitor...'
            }
            rows={3}
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isLoading}
            variant={isWin ? 'default' : 'destructive'}
          >
            {isLoading
              ? 'Saving...'
              : isWin
                ? 'Mark as Won'
                : 'Mark as Lost'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
