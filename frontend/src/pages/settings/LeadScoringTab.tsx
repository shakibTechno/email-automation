import { ScoringRuleList } from '@/components/lead-scoring/ScoringRuleList';
import { ThresholdEditor } from '@/components/lead-scoring/ThresholdEditor';

export function LeadScoringTab() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Lead Scoring</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Configure scoring rules and thresholds to automatically qualify leads based on their profile and behavior.
        </p>
      </div>
      <ThresholdEditor />
      <ScoringRuleList />
    </div>
  );
}
