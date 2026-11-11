import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import RuleEditor, { Rule } from './RuleEditor';

/**
 * Wait Until: hold the contact here until something becomes true, or give up.
 *
 * Two ways out, so both need wiring on the canvas or contacts stop dead at
 * whichever branch is missing. The panel says so rather than leaving it to be
 * discovered.
 */

interface Props {
  config: {
    rules?: Rule[];
    logic?: 'all' | 'any';
    timeout_hours?: number;
  };
  label: string;
  onChange: (config: Record<string, unknown>) => void;
  onLabelChange: (label: string) => void;
}

export default function WaitUntilConfigPanel({
  config, label, onChange, onLabelChange,
}: Props) {
  const rules = config.rules || [];
  const timeout = config.timeout_hours ?? 72;

  return (
    <div className="space-y-5">
      <div>
        <Label>Step label</Label>
        <Input
          className="mt-1"
          value={label || ''}
          onChange={(event) => onLabelChange(event.target.value)}
          placeholder="Wait for them to open it"
        />
      </div>

      <RuleEditor
        title="Wait until"
        rules={rules}
        logic={config.logic || 'all'}
        onChange={(nextRules, logic) =>
          onChange({ ...config, rules: nextRules, logic })
        }
      />

      <div>
        <Label htmlFor="timeout">Give up after (hours)</Label>
        <Input
          id="timeout"
          type="number"
          min={1}
          className="mt-1"
          value={timeout}
          onChange={(event) =>
            onChange({
              ...config,
              timeout_hours: Math.max(1, Number(event.target.value || 1)),
            })
          }
        />
        <p className="mt-1 text-xs text-muted-foreground">
          Checked every hour. A contact who satisfies the conditions straight
          away carries on immediately rather than waiting.
        </p>
      </div>

      {rules.length === 0 && (
        <p className="rounded-md border border-warning/40 bg-warning/[.08] p-3 text-xs">
          With no conditions this waits for nothing and every contact takes the
          &ldquo;met&rdquo; path at once.
        </p>
      )}

      <div className="space-y-2 rounded-lg bg-secondary/60 p-3">
        <p className="text-sm font-medium">Two ways out</p>
        <div className="space-y-1 text-xs text-muted-foreground">
          <p>
            <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-success" />
            <strong className="text-foreground">Met</strong> — the conditions
            came true in time
          </p>
          <p>
            <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-destructive" />
            <strong className="text-foreground">Timed out</strong> — they did
            not, within {timeout} hour{timeout === 1 ? '' : 's'}
          </p>
          <p className="pt-1">
            Connect both on the canvas. A contact reaching a branch with
            nothing after it stops there.
          </p>
        </div>
      </div>
    </div>
  );
}
