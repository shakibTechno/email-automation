import { Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card } from '@/components/ui/card';
import {
  ConditionalLogic,
  ConditionalCondition,
  FormField,
  defaultConditionalLogic,
} from '@/types/form';

const operatorOptions = [
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Does not equal' },
  { value: 'contains', label: 'Contains' },
  { value: 'not_contains', label: 'Does not contain' },
  { value: 'is_empty', label: 'Is empty' },
  { value: 'is_not_empty', label: 'Is not empty' },
  { value: 'greater_than', label: 'Greater than' },
  { value: 'less_than', label: 'Less than' },
];

interface ConditionalLogicEditorProps {
  logic: ConditionalLogic | undefined;
  onChange: (logic: ConditionalLogic) => void;
  availableFields: FormField[];
  currentFieldId?: string;
}

export const ConditionalLogicEditor = ({
  logic,
  onChange,
  availableFields,
  currentFieldId,
}: ConditionalLogicEditorProps) => {
  const l = { ...defaultConditionalLogic, ...logic };

  // Filter out current field and non-input fields from available fields for conditions
  const selectableFields = availableFields.filter(
    (f) =>
      f.id !== currentFieldId &&
      !['section', 'divider', 'hidden'].includes(f.field_type)
  );

  const update = (partial: Partial<ConditionalLogic>) => {
    onChange({ ...l, ...partial });
  };

  const addCondition = () => {
    const newCondition: ConditionalCondition = {
      field_id: selectableFields[0]?.id || '',
      operator: 'equals',
      value: '',
    };
    update({ conditions: [...l.conditions, newCondition] });
  };

  const updateCondition = (index: number, partial: Partial<ConditionalCondition>) => {
    const updated = [...l.conditions];
    updated[index] = { ...updated[index], ...partial };
    update({ conditions: updated });
  };

  const removeCondition = (index: number) => {
    update({ conditions: l.conditions.filter((_, i) => i !== index) });
  };

  const needsValue = (operator: string) =>
    !['is_empty', 'is_not_empty'].includes(operator);

  return (
    <Card className="p-3 space-y-3 bg-gray-50">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="conditional-enabled"
            checked={l.enabled}
            onCheckedChange={(c) => update({ enabled: c === true })}
          />
          <Label htmlFor="conditional-enabled" className="text-xs font-medium">
            Enable conditional logic
          </Label>
        </div>
      </div>

      {l.enabled && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <Select
              value={l.action}
              onValueChange={(v: 'show' | 'hide') => update({ action: v })}
            >
              <SelectTrigger className="w-24 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="show">Show</SelectItem>
                <SelectItem value="hide">Hide</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-muted-foreground">this field when</span>
            <Select
              value={l.logic}
              onValueChange={(v: 'all' | 'any') => update({ logic: v })}
            >
              <SelectTrigger className="w-20 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="any">Any</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-muted-foreground">
              of the following conditions are met:
            </span>
          </div>

          <div className="space-y-2">
            {l.conditions.map((condition, idx) => (
              <div key={idx} className="flex items-center gap-2 flex-wrap">
                <Select
                  value={condition.field_id}
                  onValueChange={(v) => updateCondition(idx, { field_id: v })}
                >
                  <SelectTrigger className="w-32 h-8 text-xs">
                    <SelectValue placeholder="Field" />
                  </SelectTrigger>
                  <SelectContent>
                    {selectableFields.map((f) => (
                      <SelectItem key={f.id} value={f.id || ''}>
                        {f.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={condition.operator}
                  onValueChange={(v: ConditionalCondition['operator']) =>
                    updateCondition(idx, { operator: v })
                  }
                >
                  <SelectTrigger className="w-36 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {operatorOptions.map((op) => (
                      <SelectItem key={op.value} value={op.value}>
                        {op.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {needsValue(condition.operator) && (
                  <Input
                    value={condition.value}
                    onChange={(e) => updateCondition(idx, { value: e.target.value })}
                    placeholder="Value"
                    className="w-32 h-8 text-xs"
                  />
                )}

                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => removeCondition(idx)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>

          {selectableFields.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={addCondition}
            >
              <Plus className="h-3 w-3 mr-1" /> Add Condition
            </Button>
          ) : (
            <p className="text-xs text-muted-foreground">
              Add more fields to create conditions.
            </p>
          )}
        </div>
      )}
    </Card>
  );
};
