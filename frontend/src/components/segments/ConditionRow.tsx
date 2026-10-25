import { Trash2, GripVertical } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { SegmentCondition, FieldDefinition, TagOption } from '@/types/segment';

interface ConditionRowProps {
  condition: SegmentCondition;
  fields: FieldDefinition[];
  tags: TagOption[];
  onChange: (condition: SegmentCondition) => void;
  onRemove: () => void;
  canRemove: boolean;
}

export function ConditionRow({
  condition,
  fields,
  tags,
  onChange,
  onRemove,
  canRemove,
}: ConditionRowProps) {
  const selectedField = fields.find((f) => f.field === condition.field);
  const operators = selectedField?.operators || [];

  // Check if operator requires a value
  const needsValue = !['is_empty', 'is_not_empty', 'is_true', 'is_false', 'has_no_tags'].includes(
    condition.operator
  );

  // Check if value should be multiple select
  const isMultipleValue = ['in', 'not_in', 'has_any_tag', 'has_all_tags'].includes(
    condition.operator
  );

  // Check if value should be a date range
  const isBetween = condition.operator === 'between';

  const handleFieldChange = (field: string) => {
    const newField = fields.find((f) => f.field === field);
    const newOperators = newField?.operators || [];
    const defaultOperator = newOperators[0]?.value || '';
    onChange({
      ...condition,
      field,
      operator: defaultOperator,
      value: null,
    });
  };

  const handleOperatorChange = (operator: string) => {
    onChange({
      ...condition,
      operator,
      value: isMultipleValue ? [] : null,
    });
  };

  const handleValueChange = (value: string | string[] | number | null) => {
    onChange({ ...condition, value });
  };

  const renderValueInput = () => {
    if (!needsValue) return null;

    // Tag field - show tag selector
    if (selectedField?.type === 'tag') {
      if (isMultipleValue) {
        // Multi-select tags
        const selectedTags = Array.isArray(condition.value) ? condition.value : [];
        return (
          <Select
            value={selectedTags.length > 0 ? selectedTags[0] : ''}
            onValueChange={(val) => {
              const current = Array.isArray(condition.value) ? condition.value : [];
              if (!current.includes(val)) {
                handleValueChange([...current, val]);
              }
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select tags..." />
            </SelectTrigger>
            <SelectContent>
              {tags.map((tag) => (
                <SelectItem key={tag.id} value={tag.id}>
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: tag.color }}
                    />
                    {tag.name}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      } else {
        // Single tag select
        return (
          <Select
            value={condition.value as string || ''}
            onValueChange={handleValueChange}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select tag..." />
            </SelectTrigger>
            <SelectContent>
              {tags.map((tag) => (
                <SelectItem key={tag.id} value={tag.id}>
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: tag.color }}
                    />
                    {tag.name}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      }
    }

    // Select field with options
    if (selectedField?.type === 'select' && selectedField.options) {
      if (isMultipleValue) {
        // Multi-select for select fields
        const selected = Array.isArray(condition.value) ? condition.value : [];
        return (
          <Select
            value={selected.length > 0 ? selected[0] : ''}
            onValueChange={(val) => {
              const current = Array.isArray(condition.value) ? condition.value : [];
              if (!current.includes(val)) {
                handleValueChange([...current, val]);
              }
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select values..." />
            </SelectTrigger>
            <SelectContent>
              {selectedField.options.map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      } else {
        return (
          <Select
            value={condition.value as string || ''}
            onValueChange={handleValueChange}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select value..." />
            </SelectTrigger>
            <SelectContent>
              {selectedField.options.map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      }
    }

    // Number field
    if (selectedField?.type === 'number') {
      if (isBetween) {
        const values = Array.isArray(condition.value) ? condition.value : ['', ''];
        return (
          <div className="flex w-full items-center gap-2">
            <Input
              type="number"
              placeholder="Min"
              value={values[0] || ''}
              onChange={(e) => handleValueChange([e.target.value, values[1] || ''])}
              className="w-full"
            />
            <span className="shrink-0 text-muted-foreground">and</span>
            <Input
              type="number"
              placeholder="Max"
              value={values[1] || ''}
              onChange={(e) => handleValueChange([values[0] || '', e.target.value])}
              className="w-full"
            />
          </div>
        );
      }
      return (
        <Input
          type="number"
          placeholder="Value"
          value={condition.value as number || ''}
          onChange={(e) => handleValueChange(e.target.value ? Number(e.target.value) : null)}
          className="w-full"
        />
      );
    }

    // Date field
    if (selectedField?.type === 'date') {
      if (condition.operator === 'in_last_days' || condition.operator === 'more_than_days_ago') {
        return (
          <div className="flex w-full items-center gap-2">
            <Input
              type="number"
              placeholder="Days"
              value={condition.value as number || ''}
              onChange={(e) => handleValueChange(e.target.value ? Number(e.target.value) : null)}
              className="w-full"
            />
            <span className="shrink-0 text-muted-foreground">days</span>
          </div>
        );
      }
      if (isBetween) {
        const values = Array.isArray(condition.value) ? condition.value : ['', ''];
        return (
          <div className="flex w-full items-center gap-2">
            <Input
              type="date"
              value={values[0] || ''}
              onChange={(e) => handleValueChange([e.target.value, values[1] || ''])}
              className="w-full"
            />
            <span className="shrink-0 text-muted-foreground">and</span>
            <Input
              type="date"
              value={values[1] || ''}
              onChange={(e) => handleValueChange([values[0] || '', e.target.value])}
              className="w-full"
            />
          </div>
        );
      }
      return (
        <Input
          type="date"
          value={condition.value as string || ''}
          onChange={(e) => handleValueChange(e.target.value)}
          className="w-full"
        />
      );
    }

    // Default: string input
    return (
      <Input
        placeholder="Value"
        value={condition.value as string || ''}
        onChange={(e) => handleValueChange(e.target.value)}
        className="w-full"
      />
    );
  };

  return (
    // A grid, not a flex row: every condition gets the same columns, so field,
    // operator and value line up down the list however each row's operator
    // renders. As a flex row each value control carried its own width (w-48 for
    // text, w-40 for a date, w-24 for a day count), so stacked conditions ended
    // their value input at different places and left a dead gap before the
    // remove button. The value track also holds its width when the operator
    // takes no value at all, such as "is empty".
    <div className="grid grid-cols-[auto_10rem_11rem_minmax(0,1fr)_auto] items-center gap-2 rounded-lg bg-muted/30 p-3">
      <GripVertical className="h-4 w-4 cursor-grab text-muted-foreground" />

      {/* Field selector */}
      <Select value={condition.field} onValueChange={handleFieldChange}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select field..." />
        </SelectTrigger>
        <SelectContent>
          {fields.map((field) => (
            <SelectItem key={field.field} value={field.field}>
              {field.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Operator selector */}
      <Select value={condition.operator} onValueChange={handleOperatorChange}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select operator..." />
        </SelectTrigger>
        <SelectContent>
          {operators.map((op) => (
            <SelectItem key={op.value} value={op.value}>
              {op.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Value input — the wrapper holds the column open for operators such as
          "is empty" that render no control. */}
      <div className="flex min-w-0 items-center">{renderValueInput()}</div>

      {/* Remove button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onRemove}
        disabled={!canRemove}
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}
