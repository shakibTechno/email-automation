import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import RuleEditor, { Rule } from './RuleEditor';

/**
 * If/Else: two paths, one question.
 *
 * The rule editor is shared with Wait Until and Split by Rule. This panel
 * used to carry its own hardcoded list of ten contact fields — a fourth
 * definition of "what fields a contact has" — and offered "has_tag" with a
 * free-text box, so using it meant pasting a tag's UUID by hand. Fields now
 * come from the same place the executor evaluates them against.
 */

interface Props {
  config: {
    rules?: Rule[];
    logic?: 'all' | 'any';
  };
  label: string;
  onChange: (config: Record<string, unknown>) => void;
  onLabelChange: (label: string) => void;
}

export default function ConditionConfigPanel({
  config, label, onChange, onLabelChange,
}: Props) {
  const rules = config.rules || [];

  return (
    <div className="space-y-5">
      <div>
        <Label>Step label</Label>
        <Input
          className="mt-1"
          value={label || ''}
          onChange={(event) => onLabelChange(event.target.value)}
          placeholder="Did they open it?"
        />
      </div>

      <RuleEditor
        rules={rules}
        logic={config.logic || 'all'}
        onChange={(nextRules, logic) =>
          onChange({ ...config, rules: nextRules, logic })
        }
      />

      {rules.length === 0 && (
        <p className="rounded-md border border-warning/40 bg-warning/[.08] p-3 text-xs">
          With no conditions every contact takes the true path, which reads as
          the condition being ignored.
        </p>
      )}

      <div className="space-y-2 rounded-lg bg-secondary/60 p-3">
        <p className="text-sm font-medium">Two ways out</p>
        <div className="space-y-1 text-xs text-muted-foreground">
          <p>
            <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-success" />
            <strong className="text-foreground">True</strong> — the conditions
            match
          </p>
          <p>
            <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-destructive" />
            <strong className="text-foreground">False</strong> — they do not
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
