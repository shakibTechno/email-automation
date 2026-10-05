import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Trash2, Plus } from 'lucide-react';
import { useScoreThresholds, useBulkUpdateThresholds } from '@/hooks/useLeadScoring';
import type { ScoreThresholdInput } from '@/types/leadScoring';

const COLOR_OPTIONS = [
  { value: 'gray',   label: 'Gray',   cls: 'bg-muted-foreground' },
  { value: 'blue',   label: 'Blue',   cls: 'bg-info' },
  { value: 'green',  label: 'Green',  cls: 'bg-success' },
  { value: 'yellow', label: 'Yellow', cls: 'bg-warning' },
  { value: 'orange', label: 'Orange', cls: 'bg-orange-400' },
  { value: 'red',    label: 'Red',    cls: 'bg-red-400' },
  { value: 'purple', label: 'Purple', cls: 'bg-purple-400' },
];

const ENGAGEMENT_OPTIONS = [
  { value: 'none',   label: 'None (Inactive)' },
  { value: 'low',    label: 'Low (Cold)' },
  { value: 'medium', label: 'Medium (Warm)' },
  { value: 'high',   label: 'High (Hot)' },
];

const DEFAULT_THRESHOLDS: ScoreThresholdInput[] = [
  { label: 'Inactive', min_score: 0,  color: 'gray',   engagement_level: 'none' },
  { label: 'Cold',     min_score: 10, color: 'blue',   engagement_level: 'low' },
  { label: 'Warm',     min_score: 40, color: 'yellow', engagement_level: 'medium' },
  { label: 'Hot',      min_score: 70, color: 'red',    engagement_level: 'high' },
];

export function ThresholdEditor() {
  const { data: saved, isLoading } = useScoreThresholds();
  const bulkUpdate = useBulkUpdateThresholds();
  const [rows, setRows] = useState<ScoreThresholdInput[]>(DEFAULT_THRESHOLDS);

  useEffect(() => {
    if (saved && saved.length > 0) {
      setRows(saved.map(({ label, min_score, color, engagement_level }) => ({
        label, min_score, color, engagement_level,
      })));
    }
  }, [saved]);

  function updateRow(index: number, field: keyof ScoreThresholdInput, value: string | number) {
    setRows((prev) => prev.map((r, i) => i === index ? { ...r, [field]: value } : r));
  }

  function addRow() {
    setRows((prev) => [
      ...prev,
      { label: 'New Level', min_score: 0, color: 'blue', engagement_level: 'none' },
    ]);
  }

  function removeRow(index: number) {
    setRows((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSave() {
    const sorted = [...rows].sort((a, b) => a.min_score - b.min_score);
    bulkUpdate.mutate(sorted);
  }

  if (isLoading) {
    return <div className="h-40 flex items-center justify-center text-sm text-muted-foreground">Loading thresholds…</div>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Score Thresholds</CardTitle>
        <p className="text-sm text-muted-foreground">
          Define score ranges and their engagement labels. Contacts are automatically assigned the highest matching threshold.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          {rows.map((row, i) => (
            <div key={i} className="grid grid-cols-[1fr_80px_120px_130px_36px] gap-2 items-end">
              <div>
                {i === 0 && <Label className="text-xs mb-1 block">Label</Label>}
                <Input
                  value={row.label}
                  onChange={(e) => updateRow(i, 'label', e.target.value)}
                  placeholder="Label"
                />
              </div>
              <div>
                {i === 0 && <Label className="text-xs mb-1 block">Min Score</Label>}
                <Input
                  type="number"
                  min={0}
                  max={1000}
                  value={row.min_score}
                  onChange={(e) => updateRow(i, 'min_score', parseInt(e.target.value, 10) || 0)}
                />
              </div>
              <div>
                {i === 0 && <Label className="text-xs mb-1 block">Color</Label>}
                <Select
                  value={row.color}
                  onValueChange={(v) => updateRow(i, 'color', v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COLOR_OPTIONS.map((c) => (
                      <SelectItem key={c.value} value={c.value}>
                        <div className="flex items-center gap-2">
                          <div className={`h-3 w-3 rounded-full ${c.cls}`} />
                          {c.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                {i === 0 && <Label className="text-xs mb-1 block">Engagement Level</Label>}
                <Select
                  value={row.engagement_level}
                  onValueChange={(v: any) => updateRow(i, 'engagement_level', v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ENGAGEMENT_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button
                size="icon"
                variant="ghost"
                className="text-destructive hover:text-destructive"
                onClick={() => removeRow(i)}
                disabled={rows.length <= 1}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>

        <div className="flex justify-between pt-2">
          <Button variant="outline" size="sm" onClick={addRow}>
            <Plus className="h-4 w-4 mr-1.5" />
            Add Threshold
          </Button>
          <Button onClick={handleSave} disabled={bulkUpdate.isPending}>
            {bulkUpdate.isPending ? 'Saving…' : 'Save Thresholds'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
