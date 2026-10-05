import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { useCampaignComparison } from '@/hooks/useAnalytics';
import { Loader2 } from 'lucide-react';
import type { CampaignMetrics } from '@/types/analytics';

interface CampaignComparisonDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  campaigns: CampaignMetrics[];
}

export function CampaignComparisonDialog({
  open,
  onOpenChange,
  campaigns,
}: CampaignComparisonDialogProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const { data: comparison, isLoading } = useCampaignComparison(selectedIds);

  const toggleCampaign = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleClose = () => {
    setSelectedIds([]);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Compare Campaigns</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-3">
              Select 2 or more campaigns to compare:
            </p>
            <div className="space-y-2 max-h-[200px] overflow-y-auto border rounded-md p-3">
              {campaigns.map((c) => (
                <label
                  key={c.id}
                  className="flex items-center gap-3 p-2 rounded hover:bg-muted cursor-pointer"
                >
                  <Checkbox
                    checked={selectedIds.includes(c.id)}
                    onCheckedChange={() => toggleCampaign(c.id)}
                  />
                  <span className="text-sm font-medium">{c.name}</span>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {c.sent_at ? new Date(c.sent_at).toLocaleDateString() : ''}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {isLoading && selectedIds.length >= 2 && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {comparison && comparison.length >= 2 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 pr-4 font-medium">Metric</th>
                    {comparison.map((c) => (
                      <th key={c.campaign.id} className="text-right py-2 px-4 font-medium">
                        {c.campaign.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  <tr>
                    <td className="py-2 pr-4 text-muted-foreground">Recipients</td>
                    {comparison.map((c) => (
                      <td key={c.campaign.id} className="text-right py-2 px-4">
                        {c.recipient_count.toLocaleString()}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2 pr-4 text-muted-foreground">Delivered</td>
                    {comparison.map((c) => (
                      <td key={c.campaign.id} className="text-right py-2 px-4">
                        {c.delivered.toLocaleString()}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2 pr-4 text-muted-foreground">Open Rate</td>
                    {comparison.map((c) => (
                      <td key={c.campaign.id} className="text-right py-2 px-4 font-semibold">
                        {c.open_rate}%
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2 pr-4 text-muted-foreground">Click Rate</td>
                    {comparison.map((c) => (
                      <td key={c.campaign.id} className="text-right py-2 px-4 font-semibold">
                        {c.click_rate}%
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2 pr-4 text-muted-foreground">Bounce Rate</td>
                    {comparison.map((c) => (
                      <td key={c.campaign.id} className="text-right py-2 px-4">
                        {c.bounce_rate}%
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2 pr-4 text-muted-foreground">Opened</td>
                    {comparison.map((c) => (
                      <td key={c.campaign.id} className="text-right py-2 px-4">
                        {c.opened.toLocaleString()}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2 pr-4 text-muted-foreground">Clicked</td>
                    {comparison.map((c) => (
                      <td key={c.campaign.id} className="text-right py-2 px-4">
                        {c.clicked.toLocaleString()}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
