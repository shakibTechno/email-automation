import { useState } from 'react';
import { FlaskConical, Trophy, Clock } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ABTest } from '@/types/campaign';
import { useABTest } from '@/hooks/useCampaigns';
import { formatDateTime } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface ABTestPanelProps {
  campaignId: string;
  abTest: ABTest;
}

const STATUS_LABELS: Record<ABTest['status'], string> = {
  draft: 'Configured',
  testing: 'Testing',
  winner_declared: 'Winner Declared',
  completed: 'Completed',
};

const STATUS_COLORS: Record<ABTest['status'], string> = {
  draft: 'bg-secondary text-muted-foreground',
  testing: 'bg-info/[.14] text-info',
  winner_declared: 'bg-warning/[.14] text-warning',
  completed: 'bg-success/[.14] text-success',
};

const TEST_TYPE_LABELS: Record<ABTest['test_type'], string> = {
  subject: 'Subject Line',
  sender_name: 'Sender Name',
  content: 'Email Content',
};

export const ABTestPanel = ({ campaignId, abTest }: ABTestPanelProps) => {
  const { declareWinner, isDeclaring } = useABTest(campaignId);
  const [declareDialogOpen, setDeclareDialogOpen] = useState(false);
  const [selectedWinner, setSelectedWinner] = useState<'a' | 'b' | null>(null);

  const variantA = abTest.variants.find((v) => v.variant === 'a');
  const variantB = abTest.variants.find((v) => v.variant === 'b');

  const canDeclare = abTest.status === 'testing' && abTest.winner_selection === 'manual';

  const handleDeclare = async () => {
    if (!selectedWinner) return;
    await declareWinner(selectedWinner);
    setDeclareDialogOpen(false);
  };

  const winnerScore = (variant: typeof variantA) => {
    if (!variant) return 0;
    return abTest.winner_criteria === 'open_rate' ? variant.open_rate : variant.click_rate;
  };

  const isWinner = (variant: 'a' | 'b') => abTest.winner_variant === variant;
  const hasResults = abTest.status !== 'draft';

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <FlaskConical className="h-4 w-4" /> A/B Test
        </h2>
        <span
          className={cn(
            'text-xs font-medium px-2 py-1 rounded-full',
            STATUS_COLORS[abTest.status]
          )}
        >
          {STATUS_LABELS[abTest.status]}
        </span>
      </div>

      {/* Config summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div>
          <p className="text-muted-foreground text-xs">Test Type</p>
          <p className="font-medium">{TEST_TYPE_LABELS[abTest.test_type]}</p>
        </div>
        <div>
          <p className="text-muted-foreground text-xs">Test Split</p>
          <p className="font-medium">{abTest.test_percentage}% of audience</p>
        </div>
        <div>
          <p className="text-muted-foreground text-xs">Winner Criteria</p>
          <p className="font-medium capitalize">
            {abTest.winner_criteria.replace('_', ' ')}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground text-xs">Selection</p>
          <p className="font-medium capitalize">{abTest.winner_selection}</p>
        </div>
      </div>

      {/* Variant comparison */}
      {variantA && variantB && (
        <div className="grid grid-cols-2 gap-3">
          {[variantA, variantB].map((v) => {
            const label = v.variant === 'a' ? 'Variant A (Control)' : 'Variant B (Challenger)';
            const winner = isWinner(v.variant);
            return (
              <div
                key={v.variant}
                className={cn(
                  'border rounded-lg p-4 space-y-3',
                  winner && 'border-warning bg-warning/[.10]'
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold">{label}</span>
                  {winner && (
                    <span className="flex items-center gap-1 text-xs text-warning font-medium">
                      <Trophy className="h-3 w-3" /> Winner
                    </span>
                  )}
                </div>

                {/* What's different */}
                {abTest.test_type === 'subject' && (
                  <p className="text-xs text-muted-foreground truncate" title={v.subject}>
                    Subject: {v.subject || '(same as campaign)'}
                  </p>
                )}
                {abTest.test_type === 'sender_name' && (
                  <p className="text-xs text-muted-foreground">
                    Sender: {v.sender_name || '(same as campaign)'}
                  </p>
                )}
                {abTest.test_type === 'content' && (
                  <p className="text-xs text-muted-foreground">
                    Template: {v.template_name || '(same as campaign)'}
                  </p>
                )}

                {/* Stats */}
                {hasResults && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-card rounded p-2 text-center border">
                      <p className="text-muted-foreground">Sent</p>
                      <p className="font-semibold text-base">{v.sent_count.toLocaleString()}</p>
                    </div>
                    <div className="bg-card rounded p-2 text-center border">
                      <p className="text-muted-foreground">Opens</p>
                      <p className="font-semibold text-base">{v.open_count.toLocaleString()}</p>
                    </div>
                    <div className="bg-card rounded p-2 text-center border">
                      <p className="text-muted-foreground">Open Rate</p>
                      <p
                        className={cn(
                          'font-semibold text-base',
                          abTest.winner_criteria === 'open_rate' &&
                            winnerScore(v) >= winnerScore(v.variant === 'a' ? variantB : variantA) &&
                            'text-success'
                        )}
                      >
                        {v.open_rate}%
                      </p>
                    </div>
                    <div className="bg-card rounded p-2 text-center border">
                      <p className="text-muted-foreground">Click Rate</p>
                      <p
                        className={cn(
                          'font-semibold text-base',
                          abTest.winner_criteria === 'click_rate' &&
                            winnerScore(v) >= winnerScore(v.variant === 'a' ? variantB : variantA) &&
                            'text-success'
                        )}
                      >
                        {v.click_rate}%
                      </p>
                    </div>
                  </div>
                )}

                {canDeclare && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full text-xs"
                    onClick={() => {
                      setSelectedWinner(v.variant);
                      setDeclareDialogOpen(true);
                    }}
                  >
                    <Trophy className="h-3 w-3 mr-1" />
                    Declare as Winner
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Timing info */}
      {abTest.status === 'testing' && abTest.winner_selection === 'auto' && (
        <p className="text-xs text-muted-foreground flex items-center gap-1">
          <Clock className="h-3 w-3" />
          Winner will be auto-selected after {abTest.test_duration_hours}h based on{' '}
          {abTest.winner_criteria.replace('_', ' ')}
        </p>
      )}

      {abTest.winner_sent_at && (
        <p className="text-xs text-muted-foreground">
          Winner sent to remaining recipients: {formatDateTime(abTest.winner_sent_at)}
        </p>
      )}

      {/* Declare winner dialog */}
      <Dialog open={declareDialogOpen} onOpenChange={setDeclareDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Declare Variant {selectedWinner?.toUpperCase()} as Winner</DialogTitle>
            <DialogDescription>
              The winning variant will immediately be sent to all remaining recipients
              who haven't received an email yet. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeclareDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleDeclare} disabled={isDeclaring}>
              <Trophy className="h-4 w-4 mr-2" />
              {isDeclaring ? 'Declaring…' : 'Confirm Winner'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
};
