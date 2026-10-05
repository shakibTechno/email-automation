import { useState, useMemo, CSSProperties } from 'react';
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
import {
  Form,
  FormField,
  FormStyling,
  FormBranding,
  FormLayout,
  ConditionalLogic,
  ConditionalCondition,
  defaultFormStyling,
  defaultFormBranding,
  defaultFormLayout,
} from '@/types/form';

interface PublicFormRendererProps {
  form: Form;
  onSubmit: (data: Record<string, any>, gdprConsent: boolean) => void;
  isSubmitting?: boolean;
  readOnly?: boolean;
}

// Evaluate a single condition against form values
const evaluateCondition = (
  condition: ConditionalCondition,
  values: Record<string, any>
): boolean => {
  const fieldValue = values[condition.field_id];
  const compareValue = condition.value;

  switch (condition.operator) {
    case 'equals':
      return String(fieldValue || '') === String(compareValue);
    case 'not_equals':
      return String(fieldValue || '') !== String(compareValue);
    case 'contains':
      return String(fieldValue || '').toLowerCase().includes(String(compareValue).toLowerCase());
    case 'not_contains':
      return !String(fieldValue || '').toLowerCase().includes(String(compareValue).toLowerCase());
    case 'is_empty':
      return !fieldValue || (typeof fieldValue === 'string' && !fieldValue.trim());
    case 'is_not_empty':
      return !!fieldValue && (typeof fieldValue !== 'string' || !!fieldValue.trim());
    case 'greater_than':
      return Number(fieldValue) > Number(compareValue);
    case 'less_than':
      return Number(fieldValue) < Number(compareValue);
    default:
      return true;
  }
};

// Evaluate conditional logic for a field
const evaluateConditionalLogic = (
  logic: ConditionalLogic | undefined,
  values: Record<string, any>
): boolean => {
  if (!logic || !logic.enabled || logic.conditions.length === 0) {
    return true; // Always visible if no logic
  }

  const results = logic.conditions.map((c) => evaluateCondition(c, values));
  const conditionsMet = logic.logic === 'all'
    ? results.every(Boolean)
    : results.some(Boolean);

  // If action is 'show', show when conditions are met
  // If action is 'hide', hide when conditions are met
  return logic.action === 'show' ? conditionsMet : !conditionsMet;
};

// Get width class based on field width
const getWidthStyle = (width: string | undefined, columns: number): string => {
  if (columns === 1) return '100%';

  switch (width) {
    case 'half':
      return columns === 3 ? '50%' : '50%';
    case 'third':
      return columns === 3 ? '33.333%' : '33.333%';
    case 'two_thirds':
      return columns === 3 ? '66.666%' : '66.666%';
    case 'full':
    default:
      return '100%';
  }
};

export const PublicFormRenderer = ({
  form,
  onSubmit,
  isSubmitting = false,
  readOnly = false,
}: PublicFormRendererProps) => {
  const [values, setValues] = useState<Record<string, any>>({});
  const [gdprConsent, setGdprConsent] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Merge defaults with form settings
  const styling: FormStyling = useMemo(
    () => ({ ...defaultFormStyling, ...form.styling }),
    [form.styling]
  );
  const branding: FormBranding = useMemo(
    () => ({ ...defaultFormBranding, ...form.branding }),
    [form.branding]
  );
  const layout: FormLayout = useMemo(
    () => ({ ...defaultFormLayout, ...form.layout }),
    [form.layout]
  );

  const sortedFields = useMemo(
    () => [...(form.fields || [])].sort((a, b) => a.order - b.order),
    [form.fields]
  );

  // Initialize hidden field values
  useMemo(() => {
    const hiddenValues: Record<string, any> = {};
    sortedFields.forEach((field) => {
      if (field.field_type === 'hidden' && field.default_value) {
        hiddenValues[field.id || ''] = field.default_value;
      }
    });
    if (Object.keys(hiddenValues).length > 0) {
      setValues((prev) => ({ ...hiddenValues, ...prev }));
    }
  }, [sortedFields]);

  const setValue = (fieldId: string, value: any) => {
    setValues((prev) => ({ ...prev, [fieldId]: value }));
    if (errors[fieldId]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[fieldId];
        return next;
      });
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    for (const field of sortedFields) {
      const id = field.id || '';
      const value = values[id];

      // Skip validation for hidden fields and layout elements
      if (['hidden', 'section', 'divider'].includes(field.field_type)) continue;

      // Skip validation for conditionally hidden fields
      if (!evaluateConditionalLogic(field.conditional_logic, values)) continue;

      if (field.is_required) {
        if (value === undefined || value === null || (typeof value === 'string' && !value.trim())) {
          newErrors[id] = `${field.label} is required`;
          continue;
        }
      }

      if (value && typeof value === 'string' && value.trim()) {
        if (field.field_type === 'email') {
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
          if (!emailRegex.test(value)) {
            newErrors[id] = 'Please enter a valid email address';
          }
        }
        if (field.field_type === 'url') {
          try {
            new URL(value);
          } catch {
            newErrors[id] = 'Please enter a valid URL';
          }
        }
      }
    }

    if (form.show_gdpr_consent && !gdprConsent) {
      newErrors['_gdpr'] = 'You must accept to continue';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (readOnly) return;
    if (!validate()) return;
    onSubmit(values, gdprConsent);
  };

  // Build CSS styles
  const formContainerStyle: CSSProperties = {
    width: layout.formWidth,
    maxWidth: layout.maxWidth,
    margin: layout.alignment === 'center' ? '0 auto' : layout.alignment === 'right' ? '0 0 0 auto' : '0',
    padding: styling.padding,
    backgroundColor: styling.backgroundColor,
    fontFamily: styling.fontFamily,
    fontSize: styling.fontSize,
    color: styling.textColor,
    borderRadius: styling.borderRadius,
  };

  const labelStyle: CSSProperties = {
    color: styling.labelColor,
    fontSize: styling.labelFontSize,
    fontWeight: styling.labelFontWeight as any,
  };

  const inputStyle: CSSProperties = {
    backgroundColor: styling.inputStyle.backgroundColor,
    borderWidth: styling.inputStyle.borderWidth,
    borderColor: styling.borderColor,
    borderRadius: styling.inputStyle.borderRadius,
    padding: styling.inputStyle.padding,
  };

  const buttonStyle: CSSProperties = {
    backgroundColor: styling.buttonStyle.backgroundColor,
    color: styling.buttonStyle.textColor,
    borderRadius: styling.buttonStyle.borderRadius,
    fontSize: styling.buttonStyle.fontSize,
    fontWeight: styling.buttonStyle.fontWeight as any,
    padding: styling.buttonStyle.padding,
    width: styling.buttonStyle.fullWidth ? '100%' : 'auto',
  };

  const errorStyle: CSSProperties = {
    color: styling.errorColor,
    fontSize: '12px',
  };

  const fieldsContainerStyle: CSSProperties = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: layout.fieldGap,
    rowGap: layout.rowGap,
  };

  const renderField = (field: FormField) => {
    const id = field.id || '';
    const value = values[id] ?? '';
    const error = errors[id];

    // Check conditional logic
    if (!evaluateConditionalLogic(field.conditional_logic, values)) {
      return null;
    }

    // Hidden fields don't render
    if (field.field_type === 'hidden') {
      return null;
    }

    // Section header
    if (field.field_type === 'section') {
      return (
        <div
          key={id}
          style={{
            width: '100%',
            paddingTop: layout.rowGap,
            paddingBottom: '8px',
          }}
        >
          <h3 style={{
            fontSize: '16px',
            fontWeight: '600',
            color: styling.textColor,
            marginBottom: field.section_description ? '4px' : '0',
          }}>
            {field.label}
          </h3>
          {field.section_description && (
            <p style={{ fontSize: '14px', color: styling.labelColor, opacity: 0.8 }}>
              {field.section_description}
            </p>
          )}
        </div>
      );
    }

    // Divider
    if (field.field_type === 'divider') {
      return (
        <div
          key={id}
          style={{
            width: '100%',
            padding: `${layout.rowGap} 0`,
          }}
        >
          <hr style={{ border: 'none', borderTop: `1px solid ${styling.borderColor}` }} />
        </div>
      );
    }

    const fieldWidth = getWidthStyle(field.width, layout.columns);
    const common = {
      id,
      disabled: readOnly || isSubmitting,
      placeholder: field.placeholder || '',
      style: inputStyle,
    };

    let input: React.ReactNode;

    switch (field.field_type) {
      case 'textarea':
        input = (
          <Textarea
            {...common}
            value={value}
            onChange={(e) => setValue(id, e.target.value)}
            rows={3}
          />
        );
        break;

      case 'dropdown':
        input = (
          <Select
            value={value}
            onValueChange={(v) => setValue(id, v)}
            disabled={readOnly || isSubmitting}
          >
            <SelectTrigger style={inputStyle}>
              <SelectValue placeholder={field.placeholder || 'Select...'} />
            </SelectTrigger>
            <SelectContent>
              {(field.options || []).map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
        break;

      case 'radio':
        input = (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {(field.options || []).map((opt) => (
              <label
                key={opt}
                style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: styling.fontSize, cursor: 'pointer' }}
              >
                <input
                  type="radio"
                  name={id}
                  value={opt}
                  checked={value === opt}
                  onChange={() => setValue(id, opt)}
                  disabled={readOnly || isSubmitting}
                  style={{ accentColor: styling.primaryColor }}
                />
                {opt}
              </label>
            ))}
          </div>
        );
        break;

      case 'checkbox':
        if (field.options && field.options.length > 0) {
          const selected = Array.isArray(value) ? value : [];
          input = (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {field.options.map((opt) => (
                <label
                  key={opt}
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: styling.fontSize, cursor: 'pointer' }}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(opt)}
                    onChange={(e) => {
                      const next = e.target.checked
                        ? [...selected, opt]
                        : selected.filter((v: string) => v !== opt);
                      setValue(id, next);
                    }}
                    disabled={readOnly || isSubmitting}
                    style={{ accentColor: styling.primaryColor }}
                  />
                  {opt}
                </label>
              ))}
            </div>
          );
        } else {
          input = (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Checkbox
                id={id}
                checked={value === true}
                onCheckedChange={(checked) => setValue(id, checked === true)}
                disabled={readOnly || isSubmitting}
              />
              <Label htmlFor={id} style={{ ...labelStyle, fontWeight: '400' }}>
                {field.label}
              </Label>
            </div>
          );
        }
        break;

      case 'date':
        input = (
          <Input
            {...common}
            type="date"
            value={value}
            onChange={(e) => setValue(id, e.target.value)}
          />
        );
        break;

      case 'number':
        input = (
          <Input
            {...common}
            type="number"
            value={value}
            onChange={(e) => setValue(id, e.target.value)}
          />
        );
        break;

      case 'email':
        input = (
          <Input
            {...common}
            type="email"
            value={value}
            onChange={(e) => setValue(id, e.target.value)}
          />
        );
        break;

      case 'phone':
        input = (
          <Input
            {...common}
            type="tel"
            value={value}
            onChange={(e) => setValue(id, e.target.value)}
          />
        );
        break;

      case 'url':
        input = (
          <Input
            {...common}
            type="url"
            value={value}
            onChange={(e) => setValue(id, e.target.value)}
          />
        );
        break;

      default: // text
        input = (
          <Input
            {...common}
            type="text"
            value={value}
            onChange={(e) => setValue(id, e.target.value)}
          />
        );
    }

    // For standalone checkbox, label is rendered inline
    if (field.field_type === 'checkbox' && (!field.options || field.options.length === 0)) {
      return (
        <div
          key={id}
          style={{
            width: fieldWidth,
            minWidth: 0,
            boxSizing: 'border-box',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {input}
            {field.help_text && (
              <p style={{ fontSize: '12px', color: styling.labelColor, opacity: 0.8 }}>{field.help_text}</p>
            )}
            {error && <p style={errorStyle}>{error}</p>}
          </div>
        </div>
      );
    }

    return (
      <div
        key={id}
        style={{
          width: fieldWidth,
          minWidth: 0,
          boxSizing: 'border-box',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <Label htmlFor={id} style={labelStyle}>
            {field.label}
            {field.is_required && <span style={{ color: styling.errorColor, marginLeft: '4px' }}>*</span>}
          </Label>
          {input}
          {field.help_text && (
            <p style={{ fontSize: '12px', color: styling.labelColor, opacity: 0.8 }}>{field.help_text}</p>
          )}
          {error && <p style={errorStyle}>{error}</p>}
        </div>
      </div>
    );
  };

  return (
    <div className="form-container" style={formContainerStyle}>
      {/* Custom CSS injection */}
      {branding.customCss && (
        <style dangerouslySetInnerHTML={{ __html: branding.customCss }} />
      )}

      {/* Logo */}
      {branding.logoUrl && (
        <div style={{
          textAlign: branding.logoPosition,
          marginBottom: styling.fieldSpacing,
        }}>
          <img
            src={branding.logoUrl}
            alt="Logo"
            style={{ maxHeight: branding.logoMaxHeight, maxWidth: '100%' }}
          />
        </div>
      )}

      {/* Header */}
      {branding.headerText && (
        <h2 style={{
          fontSize: branding.headerFontSize,
          fontWeight: branding.headerFontWeight as any,
          textAlign: branding.headerAlignment,
          color: styling.textColor,
          marginBottom: styling.fieldSpacing,
        }}>
          {branding.headerText}
        </h2>
      )}

      {/* Description */}
      {form.description && (
        <p style={{
          fontSize: styling.fontSize,
          color: styling.labelColor,
          marginBottom: styling.fieldSpacing,
          opacity: 0.9,
        }}>
          {form.description}
        </p>
      )}

      <form onSubmit={handleSubmit}>
        {/* Fields */}
        <div style={fieldsContainerStyle}>
          {sortedFields.map(renderField)}
        </div>

        {/* GDPR Consent */}
        {form.show_gdpr_consent && (
          <div style={{ marginTop: styling.fieldSpacing }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <Checkbox
                id="_gdpr"
                checked={gdprConsent}
                onCheckedChange={(checked) => setGdprConsent(checked === true)}
                disabled={readOnly || isSubmitting}
                style={{ marginTop: '2px' }}
              />
              <Label htmlFor="_gdpr" style={{ ...labelStyle, fontWeight: '400', lineHeight: '1.4' }}>
                {form.gdpr_consent_text || 'I agree to receive communications.'}
              </Label>
            </div>
            {errors['_gdpr'] && (
              <p style={{ ...errorStyle, marginTop: '4px' }}>{errors['_gdpr']}</p>
            )}
          </div>
        )}

        {/* Submit Button */}
        {!readOnly && (
          <div style={{ marginTop: styling.fieldSpacing }}>
            <Button
              type="submit"
              disabled={isSubmitting}
              style={buttonStyle}
              className="hover:opacity-90 transition-opacity"
            >
              {isSubmitting ? 'Submitting...' : form.submit_button_text || 'Submit'}
            </Button>
          </div>
        )}
      </form>

      {/* Footer */}
      {branding.footerText && (
        <p style={{
          fontSize: branding.footerFontSize,
          textAlign: branding.footerAlignment,
          color: styling.labelColor,
          marginTop: styling.fieldSpacing,
          opacity: 0.8,
        }}>
          {branding.footerText}
        </p>
      )}

      {/* Powered By */}
      {branding.showPoweredBy && (
        <p style={{
          fontSize: '11px',
          textAlign: 'center',
          color: styling.labelColor,
          marginTop: styling.fieldSpacing,
          opacity: 0.6,
        }}>
          Powered by Email Automation
        </p>
      )}
    </div>
  );
};
