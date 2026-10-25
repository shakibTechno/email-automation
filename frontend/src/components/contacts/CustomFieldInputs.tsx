import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCustomFields } from '@/hooks/useCustomFields';
import type { CustomField } from '@/types/contact';

type Values = Record<string, unknown>;

interface CustomFieldInputsProps {
  values: Values;
  onChange: (values: Values) => void;
  disabled?: boolean;
}

const INPUT_TYPE: Record<string, string> = {
  number: 'number',
  date: 'date',
  url: 'url',
  email: 'email',
};

/**
 * The organization's custom fields, rendered from their definitions.
 *
 * The contact form had no custom-field inputs at all, so a field could be
 * defined and then only ever populated by an import or the API. And the server
 * enforces the declared type now, which only helps if the form offers the right
 * control — a date picker for a date, a dropdown limited to its choices.
 */
export const CustomFieldInputs = ({
  values,
  onChange,
  disabled,
}: CustomFieldInputsProps) => {
  const { fields, isLoading } = useCustomFields();

  if (isLoading || fields.length === 0) return null;

  const set = (key: string, value: unknown) => onChange({ ...values, [key]: value });

  return (
    <div className="space-y-4">
      {fields.map((field) => (
        <CustomFieldInput
          key={field.id}
          field={field}
          value={values[field.key]}
          onChange={(value) => set(field.key, value)}
          disabled={disabled}
        />
      ))}
    </div>
  );
};

const CustomFieldInput = ({
  field,
  value,
  onChange,
  disabled,
}: {
  field: CustomField;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled?: boolean;
}) => {
  const id = `custom-${field.key}`;
  const label = (
    <Label htmlFor={id}>
      {field.name}
      {field.is_required && <span className="ml-1 text-destructive">*</span>}
    </Label>
  );
  const hint = field.help_text ? (
    <p className="text-[11.5px] text-muted-foreground">{field.help_text}</p>
  ) : null;

  if (field.field_type === 'boolean') {
    return (
      <label className="flex items-center gap-2 text-[13px]">
        <Checkbox
          checked={value === true}
          onCheckedChange={(v) => onChange(v === true)}
          disabled={disabled}
        />
        <span>
          {field.name}
          {hint}
        </span>
      </label>
    );
  }

  if (field.field_type === 'dropdown') {
    return (
      <div className="space-y-2">
        {label}
        <Select
          value={(value as string) || '__none'}
          onValueChange={(v) => onChange(v === '__none' ? null : v)}
          disabled={disabled}
        >
          <SelectTrigger id={id}>
            <SelectValue placeholder="Not set" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none">Not set</SelectItem>
            {field.dropdown_options.map((option) => (
              <SelectItem key={option} value={option}>
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {hint}
      </div>
    );
  }

  if (field.field_type === 'multiselect') {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div className="space-y-2">
        {label}
        {/* Checkboxes rather than a multi-select control: the choice lists here
            are short, and a native multi-select is the worst widget on the web. */}
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          {field.dropdown_options.map((option) => (
            <label key={option} className="flex items-center gap-1.5 text-[12.5px]">
              <Checkbox
                checked={selected.includes(option)}
                onCheckedChange={(v) =>
                  onChange(
                    v === true
                      ? [...selected, option]
                      : selected.filter((s) => s !== option)
                  )
                }
                disabled={disabled}
              />
              {option}
            </label>
          ))}
        </div>
        {hint}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {label}
      <Input
        id={id}
        type={INPUT_TYPE[field.field_type] ?? 'text'}
        value={value === null || value === undefined ? '' : String(value)}
        onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
        disabled={disabled}
      />
      {hint}
    </div>
  );
};
