import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Plus, Trash2 } from 'lucide-react';
import { ConditionRule } from '@/types/workflow';

interface ConditionConfigPanelProps {
  config: {
    rules?: ConditionRule[];
    logic?: 'all' | 'any';
  };
  label: string;
  onChange: (config: Record<string, unknown>) => void;
  onLabelChange: (label: string) => void;
}

const OPERATORS = [
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Does not equal' },
  { value: 'contains', label: 'Contains' },
  { value: 'not_contains', label: 'Does not contain' },
  { value: 'starts_with', label: 'Starts with' },
  { value: 'ends_with', label: 'Ends with' },
  { value: 'is_empty', label: 'Is empty' },
  { value: 'is_not_empty', label: 'Is not empty' },
  { value: 'greater_than', label: 'Greater than' },
  { value: 'less_than', label: 'Less than' },
];

const FIELDS = [
  { value: 'email', label: 'Email' },
  { value: 'first_name', label: 'First Name' },
  { value: 'last_name', label: 'Last Name' },
  { value: 'company', label: 'Company' },
  { value: 'job_title', label: 'Job Title' },
  { value: 'phone', label: 'Phone' },
  { value: 'lead_score', label: 'Lead Score' },
  { value: 'engagement_level', label: 'Engagement Level' },
  { value: 'is_subscribed', label: 'Is Subscribed' },
  { value: 'has_tag', label: 'Has Tag' },
];

export default function ConditionConfigPanel({
  config,
  label,
  onChange,
  onLabelChange,
}: ConditionConfigPanelProps) {
  const rules = config.rules || [];
  const logic = config.logic || 'all';

  const addRule = () => {
    const newRule: ConditionRule = {
      field: 'email',
      operator: 'is_not_empty',
      value: '',
    };
    onChange({
      ...config,
      rules: [...rules, newRule],
    });
  };

  const updateRule = (index: number, updates: Partial<ConditionRule>) => {
    const newRules = [...rules];
    newRules[index] = { ...newRules[index], ...updates };
    onChange({
      ...config,
      rules: newRules,
    });
  };

  const removeRule = (index: number) => {
    onChange({
      ...config,
      rules: rules.filter((_, i) => i !== index),
    });
  };

  const needsValue = (operator: string) => {
    return !['is_empty', 'is_not_empty'].includes(operator);
  };

  return (
    <div className="space-y-6">
      {/* Label */}
      <div>
        <Label>Node Label</Label>
        <Input
          value={label || ''}
          onChange={(e) => onLabelChange(e.target.value)}
          placeholder="Enter a custom label"
        />
      </div>

      {/* Logic selector */}
      <div>
        <Label>Match conditions</Label>
        <Select
          value={logic}
          onValueChange={(value) =>
            onChange({ ...config, logic: value as 'all' | 'any' })
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All conditions (AND)</SelectItem>
            <SelectItem value="any">Any condition (OR)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Rules */}
      <div className="space-y-4">
        <Label>Conditions</Label>

        {rules.length === 0 ? (
          <div className="text-center py-6 border border-dashed rounded-lg">
            <p className="text-sm text-gray-500 mb-3">No conditions added</p>
            <Button variant="outline" size="sm" onClick={addRule}>
              <Plus className="h-4 w-4 mr-2" />
              Add Condition
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {rules.map((rule, index) => (
              <div
                key={index}
                className="p-3 border rounded-lg bg-gray-50 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500">
                    Condition {index + 1}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => removeRule(index)}
                  >
                    <Trash2 className="h-3 w-3 text-red-500" />
                  </Button>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <Select
                    value={rule.field}
                    onValueChange={(value) => updateRule(index, { field: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Field" />
                    </SelectTrigger>
                    <SelectContent>
                      {FIELDS.map((field) => (
                        <SelectItem key={field.value} value={field.value}>
                          {field.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Select
                    value={rule.operator}
                    onValueChange={(value) =>
                      updateRule(index, { operator: value as ConditionRule['operator'] })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Operator" />
                    </SelectTrigger>
                    <SelectContent>
                      {OPERATORS.map((op) => (
                        <SelectItem key={op.value} value={op.value}>
                          {op.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {needsValue(rule.operator) && (
                  <Input
                    value={rule.value}
                    onChange={(e) => updateRule(index, { value: e.target.value })}
                    placeholder="Value"
                  />
                )}
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              onClick={addRule}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Condition
            </Button>
          </div>
        )}
      </div>

      {/* Branch explanation */}
      <div className="bg-amber-50 p-3 rounded-lg space-y-2">
        <p className="text-sm font-medium text-amber-800">Branch Behavior</p>
        <div className="text-xs text-amber-700 space-y-1">
          <p>
            <span className="inline-block w-3 h-3 bg-green-500 rounded-full mr-2"></span>
            <strong>True branch:</strong> Conditions match
          </p>
          <p>
            <span className="inline-block w-3 h-3 bg-red-500 rounded-full mr-2"></span>
            <strong>False branch:</strong> Conditions don't match
          </p>
        </div>
      </div>
    </div>
  );
}
