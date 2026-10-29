import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronUp,
  ChevronDown,
  Trash2,
  GripVertical,
  Plus,
  X,
  Settings2,
} from 'lucide-react';
import { formsApi } from '@/api/forms';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card } from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ConditionalLogicEditor } from './ConditionalLogicEditor';
import { FormField, FieldType, FieldWidth, defaultConditionalLogic } from '@/types/form';

const fieldTypeOptions: { value: FieldType; label: string; group?: string }[] = [
  { value: 'text', label: 'Text', group: 'Basic' },
  { value: 'email', label: 'Email', group: 'Basic' },
  { value: 'phone', label: 'Phone', group: 'Basic' },
  { value: 'textarea', label: 'Textarea', group: 'Basic' },
  { value: 'number', label: 'Number', group: 'Basic' },
  { value: 'date', label: 'Date', group: 'Basic' },
  { value: 'url', label: 'URL', group: 'Basic' },
  { value: 'dropdown', label: 'Dropdown', group: 'Choice' },
  { value: 'radio', label: 'Radio Buttons', group: 'Choice' },
  { value: 'checkbox', label: 'Checkbox', group: 'Choice' },
  { value: 'hidden', label: 'Hidden', group: 'Special' },
  { value: 'section', label: 'Section Header', group: 'Layout' },
  { value: 'divider', label: 'Divider', group: 'Layout' },
];

const widthOptions: { value: FieldWidth; label: string }[] = [
  { value: 'full', label: 'Full Width' },
  { value: 'half', label: 'Half (1/2)' },
  { value: 'third', label: 'Third (1/3)' },
  { value: 'two_thirds', label: 'Two Thirds (2/3)' },
];

/**
 * What a form field may be mapped to.
 *
 * This used to be a list of six written out here, while the backend accepted
 * every writable contact column and the organization's own custom fields. A
 * form could not capture anything added to the contact after the list was
 * typed, which is the whole reason it is fetched now.
 *
 * `useQuery` with a long staleTime: the answer changes only when someone adds
 * a custom field, and every field editor on the page shares the one result.
 */
const useContactFieldOptions = () =>
  useQuery({
    queryKey: ['forms', 'contact-field-options'],
    queryFn: formsApi.getContactFieldOptions,
    staleTime: 5 * 60 * 1000,
  });

const hasOptions = (type: FieldType) =>
  ['dropdown', 'radio', 'checkbox'].includes(type);

const isLayoutField = (type: FieldType) =>
  ['section', 'divider'].includes(type);

const isHiddenField = (type: FieldType) => type === 'hidden';

interface FormFieldEditorProps {
  field: FormField;
  index: number;
  total: number;
  allFields: FormField[];
  onChange: (field: FormField) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

export const FormFieldEditor = ({
  field,
  index,
  total,
  allFields,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
}: FormFieldEditorProps) => {
  const { data: mappingOptions = [] } = useContactFieldOptions();
  const [newOption, setNewOption] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const update = (partial: Partial<FormField>) => {
    onChange({ ...field, ...partial });
  };

  const addOption = () => {
    if (newOption.trim()) {
      update({ options: [...(field.options || []), newOption.trim()] });
      setNewOption('');
    }
  };

  const removeOption = (idx: number) => {
    const opts = [...(field.options || [])];
    opts.splice(idx, 1);
    update({ options: opts });
  };

  const getFieldTypeLabel = (type: FieldType) => {
    const opt = fieldTypeOptions.find((o) => o.value === type);
    return opt?.label || type;
  };

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
          <span className="text-sm font-medium text-muted-foreground">
            {index + 1}. {getFieldTypeLabel(field.field_type)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={onMoveUp}
            disabled={index === 0}
          >
            <ChevronUp className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={onMoveDown}
            disabled={index === total - 1}
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-destructive hover:text-destructive"
            onClick={onRemove}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label className="text-xs">Field Type</Label>
          <Select
            value={field.field_type}
            onValueChange={(v: FieldType) => update({ field_type: v })}
          >
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {fieldTypeOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label className="text-xs">
            {isLayoutField(field.field_type) ? 'Section Title' : 'Label'}
          </Label>
          <Input
            className="mt-1"
            value={field.label}
            onChange={(e) => update({ label: e.target.value })}
            placeholder={isLayoutField(field.field_type) ? 'Section title...' : 'Field label'}
          />
        </div>

        {/* Section description for section headers */}
        {field.field_type === 'section' && (
          <div className="sm:col-span-2">
            <Label className="text-xs">Section Description</Label>
            <Textarea
              className="mt-1"
              value={field.section_description || ''}
              onChange={(e) => update({ section_description: e.target.value })}
              placeholder="Optional description for this section..."
              rows={2}
            />
          </div>
        )}

        {/* Hidden field default value */}
        {isHiddenField(field.field_type) && (
          <div className="sm:col-span-2">
            <Label className="text-xs">Default Value</Label>
            <Input
              className="mt-1"
              value={field.default_value || ''}
              onChange={(e) => update({ default_value: e.target.value })}
              placeholder="Value to submit with the form"
            />
          </div>
        )}

        {/* Standard fields */}
        {!isLayoutField(field.field_type) && !isHiddenField(field.field_type) && (
          <>
            <div>
              <Label className="text-xs">Placeholder</Label>
              <Input
                className="mt-1"
                value={field.placeholder || ''}
                onChange={(e) => update({ placeholder: e.target.value })}
                placeholder="Placeholder text"
              />
            </div>
            <div>
              <Label className="text-xs">Help Text</Label>
              <Input
                className="mt-1"
                value={field.help_text || ''}
                onChange={(e) => update({ help_text: e.target.value })}
                placeholder="Help text"
              />
            </div>
          </>
        )}

        {/* Width selector for all fields */}
        <div>
          <Label className="text-xs">Width</Label>
          <Select
            value={field.width || 'full'}
            onValueChange={(v: FieldWidth) => update({ width: v })}
          >
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {widthOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Contact mapping - only for input fields */}
        {!isLayoutField(field.field_type) && !isHiddenField(field.field_type) && (
          <div>
            <Label className="text-xs">Map to Contact Field</Label>
            <Select
              value={field.contact_field_mapping || ''}
              onValueChange={(v) => update({ contact_field_mapping: v === '_none' ? '' : v })}
            >
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="No mapping" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">No mapping</SelectItem>
                {mappingOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.group === 'Custom fields' ? `${opt.label} (custom)` : opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Required toggle - only for input fields */}
        {!isLayoutField(field.field_type) && !isHiddenField(field.field_type) && (
          <div className="flex items-end">
            <div className="flex items-center space-x-2 pb-2">
              <Checkbox
                id={`required-${index}`}
                checked={field.is_required}
                onCheckedChange={(checked) =>
                  update({ is_required: checked === true })
                }
              />
              <Label htmlFor={`required-${index}`} className="text-xs">
                Required field
              </Label>
            </div>
          </div>
        )}
      </div>

      {/* Options editor for dropdown/radio/checkbox */}
      {hasOptions(field.field_type) && (
        <div className="space-y-2">
          <Label className="text-xs">Options</Label>
          <div className="space-y-1">
            {(field.options || []).map((opt, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <Input
                  value={opt}
                  onChange={(e) => {
                    const opts = [...(field.options || [])];
                    opts[idx] = e.target.value;
                    update({ options: opts });
                  }}
                  className="h-8 text-sm"
                />
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 shrink-0"
                  onClick={() => removeOption(idx)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              value={newOption}
              onChange={(e) => setNewOption(e.target.value)}
              placeholder="Add option..."
              className="h-8 text-sm"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addOption();
                }
              }}
            />
            <Button
              variant="outline"
              size="sm"
              className="h-8 shrink-0"
              onClick={addOption}
            >
              <Plus className="h-3 w-3 mr-1" /> Add
            </Button>
          </div>
        </div>
      )}

      {/* Advanced settings (collapsible) */}
      {!isLayoutField(field.field_type) && field.field_type !== 'divider' && (
        <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="h-7 text-xs w-full justify-start">
              <Settings2 className="h-3 w-3 mr-1" />
              {showAdvanced ? 'Hide' : 'Show'} Advanced Settings
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-3 space-y-3">
            {/* Conditional Logic */}
            <div>
              <Label className="text-xs mb-2 block">Conditional Logic</Label>
              <ConditionalLogicEditor
                logic={field.conditional_logic || defaultConditionalLogic}
                onChange={(logic) => update({ conditional_logic: logic })}
                availableFields={allFields}
                currentFieldId={field.id}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}
    </Card>
  );
};
