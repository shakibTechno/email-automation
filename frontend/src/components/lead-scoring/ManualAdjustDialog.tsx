import { useState } from 'react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useAdjustScore } from '@/hooks/useScoreHistory';

interface Props {
  contactId: string;
  currentScore: number;
  open: boolean;
  onClose: () => void;
}

export function ManualAdjustDialog({ contactId, currentScore, open, onClose }: Props) {
  const [delta, setDelta] = useState('');
  const [note, setNote] = useState('');
  const adjustScore = useAdjustScore(contactId);

  const deltaNum = parseInt(delta, 10);
  const isValid = !isNaN(deltaNum) && deltaNum !== 0;
  const projected = isValid ? Math.max(0, Math.min(1000, currentScore + deltaNum)) : currentScore;

  function handleSubmit() {
    if (!isValid) return;
    adjustScore.mutate(
      { points_delta: deltaNum, note },
      {
        onSuccess: () => {
          setDelta('');
          setNote('');
          onClose();
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Adjust Lead Score</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4 rounded-lg bg-muted p-3 text-sm">
            <div>
              <div className="text-muted-foreground">Current</div>
              <div className="text-2xl font-bold">{currentScore}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Projected</div>
              <div className={`text-2xl font-bold ${projected !== currentScore ? (projected > currentScore ? 'text-success' : 'text-destructive') : ''}`}>
                {projected}
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="delta">Points (+/-)</Label>
            <Input
              id="delta"
              type="number"
              placeholder="e.g. +10 or -5"
              value={delta}
              onChange={(e) => setDelta(e.target.value)}
            />
            {delta && !isValid && (
              <p className="text-xs text-destructive">Enter a non-zero integer.</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="note">Note (optional)</Label>
            <Textarea
              id="note"
              rows={2}
              placeholder="Reason for adjustment..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            disabled={!isValid || adjustScore.isPending}
          >
            {adjustScore.isPending ? 'Saving…' : 'Apply'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
