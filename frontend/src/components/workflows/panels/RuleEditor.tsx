import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { useFieldDefinitions, useSegments } from '@/hooks/useSegments';
import { useRuleFields } from '@/hooks/useNodeCatalog';
import { useForms } from '@/hooks/useForms';
import { useTags } from '@/hooks/useTags';
import { BehaviourRuleField } from '@/types/workflow';

/**
 * The rules a condition, a switch path or a Wait Until tests.
 *
 * Two sources, both of them the ones the executor actually uses:
 *
 *   * contact properties come from the segments field-definitions endpoint,
 *     because the executor hands those rules to SegmentEvaluator — so a
 *     workflow condition and a segment rule cannot mean different things
 *   * behaviour fields come from the node catalogue, which the executor also
 *     reads
 *
 * The panel this replaced had its own hardcoded list of ten contact fields: a
 * fourth definition of "what fields a contact has", after the field registry,
 * the segment engine and the import mapper. It also offered "has_tag" with a
 * free-text box, so using it meant pasting a tag's UUID by hand.
 */

export interface Rule {
  field: string;
  operator: string;
  value: string;
}

interface Props {
  rules: Rule[];
  logic: 'all' | 'any';
  onChange: (rules: Rule[], logic: 'all' | 'any') => void;
  /** Shown above the list; "Conditions" unless something fits better. */
  title?: string;
}

const EMPTY = '__none__';

/** The value box a behaviour field wants: an asset picker, a path, or nothing. */
function BehaviourValue({
  spec, value, onChange,
}: {
  spec: BehaviourRuleField;
  value: string;
  onChange: (value: string) => void;
}) {
  const { data: segmentData } = useSegments();
  const { forms } = useForms();

  const asset = spec.value_asset;

  if (!spec.needs_value) return null;

  if (asset) {
    const options: { id: string; label: string }[] =
      asset === 'segment'
        ? (segmentData?.results || []).map((s: any) => ({ id: s.id, label: s.name }))
        : asset === 'form'
          ? (forms || []).map((f: any) => ({ id: f.id, label: f.name }))
          : [];

    return (
      <Select
        value={value || EMPTY}
        onValueChange={(next) => onChange(next === EMPTY ? '' : next)}
      >
        <SelectTrigger>
          <SelectValue placeholder={spec.value_label || 'Choose one'} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={EMPTY}>Any</SelectItem>
          {options.map((option) => (
            <SelectItem key={option.id} value={option.id}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  return (
    <Input
      value={value}
      placeholder={spec.value_label || 'Value'}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export default function RuleEditor({
  rules, logic, onChange, title = 'Conditions',
}: Props) {
  const { data: contactFields = [] } = useFieldDefinitions();
  const { data: ruleFields } = useRuleFields();
  const { tags } = useTags();

  const behaviour = ruleFields?.behaviour?.length
    ? ruleFields.behaviour
    : BEHAVIOUR_FALLBACK;
  const behaviourOperators = ruleFields?.behaviour_operators?.length
    ? ruleFields.behaviour_operators
    : [
        { value: 'is_true', label: 'is true' },
        { value: 'is_false', label: 'is not true' },
      ];

  const behaviourByField = Object.fromEntries(
    behaviour.map((spec) => [spec.field, spec]),
  );

  const specFor = (field: string): BehaviourRuleField | undefined =>
    behaviourByField[field];
  const contactFieldFor = (field: string) =>
    contactFields.find((definition: any) => definition.field === field);

  const update = (index: number, partial: Partial<Rule>) =>
    onChange(
      rules.map((rule, i) => (i === index ? { ...rule, ...partial } : rule)),
      logic,
    );

  const addRule = () =>
    onChange(
      [...rules, { field: 'event.email_opened', operator: 'is_true', value: '' }],
      logic,
    );

  const removeRule = (index: number) =>
    onChange(rules.filter((_, i) => i !== index), logic);

  /** Changing the field changes which operators make sense. */
  const changeField = (index: number, field: string) => {
    const spec = specFor(field);
    if (spec) {
      update(index, { field, operator: 'is_true', value: '' });
      return;
    }
    const definition: any = contactFieldFor(field);
    update(index, {
      field,
      operator: definition?.operators?.[0]?.value || 'equals',
      value: '',
    });
  };

  const operatorsFor = (field: string): { value: string; label: string }[] => {
    if (specFor(field)) return behaviourOperators;
    const definition: any = contactFieldFor(field);
    return definition?.operators || [{ value: 'equals', label: 'Equals' }];
  };

  return (
    <div className="space-y-3">
      <div>
        <Label>Match</Label>
        <Select
          value={logic}
          onValueChange={(value) => onChange(rules, value as 'all' | 'any')}
        >
          <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All of them</SelectItem>
            <SelectItem value="any">Any of them</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Label>{title}</Label>

      {rules.length === 0 ? (
        <div className="rounded-lg border border-dashed py-5 text-center">
          <p className="mb-3 text-sm text-muted-foreground">
            No conditions yet — every contact would take the same path.
          </p>
          <Button variant="outline" size="sm" onClick={addRule}>
            <Plus className="mr-2 h-4 w-4" />
            Add a condition
          </Button>
        </div>
      ) : (
        <div className="space-y-2.5">
          {rules.map((rule, index) => {
            const spec = specFor(rule.field);
            const definition: any = contactFieldFor(rule.field);
            const isTagRule = definition?.type === 'tag';
            const needsValue =
              spec
                ? Boolean(spec.needs_value)
                : !['is_empty', 'is_not_empty', 'is_true', 'is_false'].includes(
                    rule.operator,
                  );

            return (
              <div
                key={index}
                className="space-y-2 rounded-lg border bg-secondary/50 p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">
                    Condition {index + 1}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => removeRule(index)}
                  >
                    <Trash2 className="h-3 w-3 text-destructive" />
                  </Button>
                </div>

                <Select
                  value={rule.field}
                  onValueChange={(value) => changeField(index, value)}
                >
                  <SelectTrigger><SelectValue placeholder="Field" /></SelectTrigger>
                  <SelectContent>
                    {/* What they did, then what they are. Behaviour first
                        because it is what a drip workflow asks about. */}
                    {behaviour.map((entry) => (
                      <SelectItem key={entry.field} value={entry.field}>
                        {entry.label}
                      </SelectItem>
                    ))}
                    {contactFields.map((entry: any) => (
                      <SelectItem key={entry.field} value={entry.field}>
                        {entry.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={rule.operator}
                  onValueChange={(value) => update(index, { operator: value })}
                >
                  <SelectTrigger><SelectValue placeholder="Is" /></SelectTrigger>
                  <SelectContent>
                    {operatorsFor(rule.field).map((operator) => (
                      <SelectItem key={operator.value} value={operator.value}>
                        {operator.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {spec ? (
                  <BehaviourValue
                    spec={spec}
                    value={rule.value}
                    onChange={(value) => update(index, { value })}
                  />
                ) : (
                  needsValue && (
                    isTagRule ? (
                      // A tag rule wants a tag, not its UUID typed by hand.
                      <Select
                        value={rule.value || EMPTY}
                        onValueChange={(value) =>
                          update(index, { value: value === EMPTY ? '' : value })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Choose a tag" />
                        </SelectTrigger>
                        <SelectContent>
                          {tags.map((tag: any) => (
                            <SelectItem key={tag.id} value={tag.id}>
                              {tag.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        value={rule.value}
                        placeholder="Value"
                        onChange={(event) =>
                          update(index, { value: event.target.value })
                        }
                      />
                    )
                  )
                )}
              </div>
            );
          })}

          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={addRule}
          >
            <Plus className="mr-2 h-4 w-4" />
            Add a condition
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * Used only if the catalogue request has not landed yet.
 *
 * Deliberately minimal — the server's list is the real one, and a long
 * fallback here would become the second definition this component exists to
 * remove.
 */
const BEHAVIOUR_FALLBACK: BehaviourRuleField[] = [
  {
    field: 'event.email_opened',
    label: 'Opened an email in this workflow',
    type: 'behaviour',
    needs_value: false,
  },
  {
    field: 'event.email_clicked',
    label: 'Clicked an email in this workflow',
    type: 'behaviour',
    needs_value: false,
  },
];
