import { useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Settings, RefreshCw, User } from 'lucide-react';
import { useScoreHistory, useRecalculateScore } from '@/hooks/useScoreHistory';
import { ManualAdjustDialog } from './ManualAdjustDialog';
import { formatDateTime } from '@/lib/utils';
import type { ScoreHistoryEntry } from '@/types/leadScoring';

interface Props {
  contactId: string;
  currentScore: number;
  open: boolean;
  onClose: () => void;
}

function DeltaBadge({ delta }: { delta: number }) {
  const positive = delta >= 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 font-mono text-xs font-bold ${
        positive ? 'text-green-600' : 'text-red-600'
      }`}
    >
      {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
      {positive ? '+' : ''}{delta}
    </span>
  );
}

function ReasonIcon({ reason }: { reason: ScoreHistoryEntry['reason'] }) {
  if (reason === 'manual') return <User className="h-3.5 w-3.5 text-purple-500" />;
  if (reason === 'recalculation') return <RefreshCw className="h-3.5 w-3.5 text-blue-500" />;
  return <Settings className="h-3.5 w-3.5 text-orange-500" />;
}

export function ScoreHistoryDrawer({ contactId, currentScore, open, onClose }: Props) {
  const [adjustOpen, setAdjustOpen] = useState(false);
  const { data, isLoading } = useScoreHistory(contactId);
  const recalculate = useRecalculateScore(contactId);

  const entries = data?.results ?? [];

  return (
    <>
      <Sheet open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader className="pb-4">
            <SheetTitle className="flex items-center justify-between">
              <span>Score History</span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => recalculate.mutate()}
                  disabled={recalculate.isPending}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  Recalculate
                </Button>
                <Button size="sm" onClick={() => setAdjustOpen(true)}>
                  Adjust Score
                </Button>
              </div>
            </SheetTitle>
          </SheetHeader>

          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded-md" />
              ))}
            </div>
          ) : entries.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              No score history yet.
            </div>
          ) : (
            <div className="space-y-2">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-start justify-between rounded-lg border p-3 text-sm"
                >
                  <div className="flex items-start gap-2.5">
                    <div className="mt-0.5">
                      <ReasonIcon reason={entry.reason} />
                    </div>
                    <div>
                      <div className="font-medium leading-snug">
                        {entry.rule?.name ?? (entry.reason === 'manual' ? 'Manual adjustment' : 'Full recalculation')}
                      </div>
                      {entry.note && (
                        <div className="text-xs text-muted-foreground mt-0.5">{entry.note}</div>
                      )}
                      <div className="text-xs text-muted-foreground mt-1">
                        {formatDateTime(entry.created_at)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-4">
                    <DeltaBadge delta={entry.points_delta} />
                    <div className="text-xs text-muted-foreground mt-1">
                      {entry.score_before} → {entry.score_after}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SheetContent>
      </Sheet>

      <ManualAdjustDialog
        contactId={contactId}
        currentScore={currentScore}
        open={adjustOpen}
        onClose={() => setAdjustOpen(false)}
      />
    </>
  );
}
