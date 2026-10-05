import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ConditionRow } from './ConditionRow';
import type { SegmentRules, SegmentCondition, FieldDefinition, TagOption } from '@/types/segment';
import { v4 as uuidv4 } from 'uuid';

interface RuleBuilderProps {
  rules: SegmentRules;
  fields: FieldDefinition[];
  tags: TagOption[];
  onChange: (rules: SegmentRules) => void;
}

export function RuleBuilder({ rules, fields, tags, onChange }: RuleBuilderProps) {
  const handleMatchTypeChange = (matchType: 'all' | 'any') => {
    onChange({ ...rules, match_type: matchType });
  };

  const handleConditionChange = (index: number, condition: SegmentCondition) => {
    const newConditions = [...rules.conditions];
    newConditions[index] = condition;
    onChange({ ...rules, conditions: newConditions });
  };

  const handleAddCondition = () => {
    const defaultField = fields[0]?.field || 'email';
    const fieldDef = fields.find((f) => f.field === defaultField);
    const defaultOperator = fieldDef?.operators[0]?.value || 'equals';

    const newCondition: SegmentCondition = {
      id: uuidv4(),
      field: defaultField,
      operator: defaultOperator,
      value: null,
    };
    onChange({ ...rules, conditions: [...rules.conditions, newCondition] });
  };

  const handleRemoveCondition = (index: number) => {
    const newConditions = rules.conditions.filter((_, i) => i !== index);
    onChange({ ...rules, conditions: newConditions });
  };

  const hasConditions = rules.conditions.length > 0;

  return (
    <div className="space-y-4">
      {/* Match type selector */}
      <div className="flex items-center gap-3">
        <Label className="text-sm font-medium">Match</Label>
        <Select value={rules.match_type} onValueChange={handleMatchTypeChange}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All (AND)</SelectItem>
            <SelectItem value="any">Any (OR)</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">of the following conditions</span>
      </div>

      {/* Conditions list */}
      <div className="space-y-2">
        {rules.conditions.map((condition, index) => (
          <ConditionRow
            key={condition.id}
            condition={condition}
            fields={fields}
            tags={tags}
            onChange={(c) => handleConditionChange(index, c)}
            onRemove={() => handleRemoveCondition(index)}
            canRemove={rules.conditions.length > 1}
          />
        ))}

        {!hasConditions && (
          <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
            No conditions added yet. Add a condition to define your segment.
          </div>
        )}
      </div>

      {/* Add condition button */}
      <Button variant="outline" onClick={handleAddCondition} className="w-full">
        <Plus className="mr-2 h-4 w-4" />
        Add Condition
      </Button>
    </div>
  );
}
