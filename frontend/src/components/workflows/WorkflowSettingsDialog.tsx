import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { useSegments } from '@/hooks/useSegments';
import { Workflow } from '@/types/workflow';

/**
 * How a workflow lets people in, and when it is willing to send.
 *
 * Re-entry is the setting that matters most and was missing entirely: before
 * it existed a contact could enter a workflow once in their lifetime, so a
 * cart-abandon flow fired once per customer ever and testing a workflow
 * burned your own contact for good.
 */

export interface WorkflowSettings {
  reentry: string;
  reentry_cooldown_days: number;
  entry_segment: string | null;
  respect_quiet_hours: boolean;
  send_window_start: string;
  send_window_end: string;
  send_weekdays: number[];
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  settings: WorkflowSettings;
  onChange: (settings: WorkflowSettings) => void;
}

const DAYS = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
  { value: 6, label: 'Sun' },
];

const NO_SEGMENT = '__any__';

export default function WorkflowSettingsDialog({
  open, onOpenChange, settings, onChange,
}: Props) {
  const { data: segmentData } = useSegments();
  const segments = segmentData?.results || [];

  const set = (partial: Partial<WorkflowSettings>) =>
    onChange({ ...settings, ...partial });

  const toggleDay = (day: number) =>
    set({
      send_weekdays: settings.send_weekdays.includes(day)
        ? settings.send_weekdays.filter((d) => d !== day)
        : [...settings.send_weekdays, day].sort(),
    });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Workflow settings</DialogTitle>
          <DialogDescription>
            Who may enter this workflow, and when it is allowed to send.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <div>
            <Label>Can a contact go through this more than once?</Label>
            <Select
              value={settings.reentry}
              onValueChange={(value) => set({ reentry: value })}
            >
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="one_at_a_time">
                  Yes, but never twice at the same time
                </SelectItem>
                <SelectItem value="always">
                  Yes, every time the trigger fires
                </SelectItem>
                <SelectItem value="once">No, once ever</SelectItem>
              </SelectContent>
            </Select>
            <p className="mt-1 text-xs text-muted-foreground">
              {settings.reentry === 'once'
                ? 'A contact who has been through this once can never enter again — including you, while testing.'
                : settings.reentry === 'always'
                  ? 'Several runs for the same contact can overlap. Useful for order confirmations, risky for anything that sends email.'
                  : 'A contact can come back once their previous run has finished.'}
            </p>
          </div>

          {settings.reentry !== 'once' && (
            <div>
              <Label htmlFor="cooldown">Wait this many days before re-entry</Label>
              <Input
                id="cooldown"
                type="number"
                min={0}
                className="mt-1"
                value={settings.reentry_cooldown_days}
                onChange={(event) =>
                  set({ reentry_cooldown_days: Number(event.target.value || 0) })
                }
              />
              <p className="mt-1 text-xs text-muted-foreground">
                0 for no delay.
              </p>
            </div>
          )}

          <div>
            <Label>Only let in contacts from</Label>
            <Select
              value={settings.entry_segment || NO_SEGMENT}
              onValueChange={(value) =>
                set({ entry_segment: value === NO_SEGMENT ? null : value })
              }
            >
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Anyone" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_SEGMENT}>Anyone</SelectItem>
                {segments.map((segment: any) => (
                  <SelectItem key={segment.id} value={segment.id}>
                    {segment.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="mt-1 text-xs text-muted-foreground">
              The trigger says what happened; this says who it counts for.
            </p>
          </div>

          <div className="space-y-3 border-t pt-4">
            <div className="flex items-start space-x-2">
              <Checkbox
                id="quiet-hours"
                checked={settings.respect_quiet_hours}
                onCheckedChange={(checked) =>
                  set({ respect_quiet_hours: Boolean(checked) })
                }
              />
              <div>
                <Label htmlFor="quiet-hours">Only send during these hours</Label>
                <p className="text-xs text-muted-foreground">
                  A step that comes due outside them waits for the next
                  window — nothing is skipped. Without this, a 24-hour wait
                  lands at 3am.
                </p>
              </div>
            </div>

            {settings.respect_quiet_hours && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="from">From</Label>
                    <Input
                      id="from"
                      type="time"
                      className="mt-1"
                      value={settings.send_window_start?.slice(0, 5) || '09:00'}
                      onChange={(event) =>
                        set({ send_window_start: `${event.target.value}:00` })
                      }
                    />
                  </div>
                  <div>
                    <Label htmlFor="to">To</Label>
                    <Input
                      id="to"
                      type="time"
                      className="mt-1"
                      value={settings.send_window_end?.slice(0, 5) || '18:00'}
                      onChange={(event) =>
                        set({ send_window_end: `${event.target.value}:00` })
                      }
                    />
                  </div>
                </div>

                <div>
                  <Label>On these days</Label>
                  <div className="mt-1.5 flex flex-wrap gap-3">
                    {DAYS.map((day) => (
                      <div key={day.value} className="flex items-center space-x-1.5">
                        <Checkbox
                          id={`day-${day.value}`}
                          checked={settings.send_weekdays.includes(day.value)}
                          onCheckedChange={() => toggleDay(day.value)}
                        />
                        <Label htmlFor={`day-${day.value}`} className="font-normal">
                          {day.label}
                        </Label>
                      </div>
                    ))}
                  </div>
                  {settings.send_weekdays.length === 0 && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      None selected means every day.
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** The settings a workflow arrives with, for a builder that has not loaded one yet. */
export const defaultWorkflowSettings = (
  workflow?: Partial<Workflow>,
): WorkflowSettings => ({
  reentry: workflow?.reentry || 'one_at_a_time',
  reentry_cooldown_days: workflow?.reentry_cooldown_days ?? 0,
  entry_segment: workflow?.entry_segment ?? null,
  respect_quiet_hours: Boolean(workflow?.respect_quiet_hours),
  send_window_start: workflow?.send_window_start || '09:00:00',
  send_window_end: workflow?.send_window_end || '18:00:00',
  send_weekdays: workflow?.send_weekdays || [],
});
