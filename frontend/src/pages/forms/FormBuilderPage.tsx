import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Plus,
  Eye,
  Save,
  ChevronRight,
  ChevronLeft,
  Palette,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Card } from '@/components/ui/card';
import { FormFieldEditor } from '@/components/forms/FormFieldEditor';
import { FormPreview } from '@/components/forms/FormPreview';
import { FormDesignPanel } from '@/components/forms/FormDesignPanel';
import { EmbedCodeDialog } from '@/components/forms/EmbedCodeDialog';
import { useForms, useForm } from '@/hooks/useForms';
import {
  FormField,
  Form,
  CreateFormData,
  UpdateFormData,
  FormStyling,
  FormBranding,
  FormLayout,
  defaultFormStyling,
  defaultFormBranding,
  defaultFormLayout,
} from '@/types/form';
import { toast } from 'sonner';

const defaultField = (order: number): FormField => ({
  field_type: 'text',
  label: '',
  placeholder: '',
  help_text: '',
  is_required: false,
  options: [],
  validation_rules: {},
  order,
  contact_field_mapping: '',
  width: 'full',
});

const steps = [
  { id: 1, label: 'Fields & Settings' },
  { id: 2, label: 'Design' },
  { id: 3, label: 'Preview & Publish' },
];

export const FormBuilderPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;

  const { form: existingForm, isLoading: loadingForm } = useForm(id || '');
  const { createForm, updateForm, isCreating, isUpdating } = useForms();

  const [step, setStep] = useState(1);
  const [embedDialogOpen, setEmbedDialogOpen] = useState(false);

  // Form settings state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [submitButtonText, setSubmitButtonText] = useState('Submit');
  const [successMessage, setSuccessMessage] = useState('Thank you for your submission!');
  const [redirectUrl, setRedirectUrl] = useState('');
  const [showGdpr, setShowGdpr] = useState(false);
  const [gdprText, setGdprText] = useState(
    'I agree to receive communications and accept the privacy policy.'
  );
  const [fields, setFields] = useState<FormField[]>([
    { ...defaultField(0), field_type: 'email', label: 'Email', is_required: true, contact_field_mapping: 'email' },
  ]);

  // Design state
  const [styling, setStyling] = useState<FormStyling>(defaultFormStyling);
  const [branding, setBranding] = useState<FormBranding>(defaultFormBranding);
  const [layout, setLayout] = useState<FormLayout>(defaultFormLayout);

  // Populate form when editing
  useEffect(() => {
    if (isEdit && existingForm) {
      setName(existingForm.name);
      setDescription(existingForm.description || '');
      setSubmitButtonText(existingForm.submit_button_text || 'Submit');
      setSuccessMessage(existingForm.success_message || '');
      setRedirectUrl(existingForm.redirect_url || '');
      setShowGdpr(existingForm.show_gdpr_consent);
      setGdprText(existingForm.gdpr_consent_text || '');
      if (existingForm.fields && existingForm.fields.length > 0) {
        setFields(existingForm.fields);
      }
      // Load design settings
      if (existingForm.styling) {
        setStyling({ ...defaultFormStyling, ...existingForm.styling });
      }
      if (existingForm.branding) {
        setBranding({ ...defaultFormBranding, ...existingForm.branding });
      }
      if (existingForm.layout) {
        setLayout({ ...defaultFormLayout, ...existingForm.layout });
      }
    }
  }, [isEdit, existingForm]);

  const addField = () => {
    setFields([...fields, defaultField(fields.length)]);
  };

  const updateField = (index: number, updated: FormField) => {
    const next = [...fields];
    next[index] = updated;
    setFields(next);
  };

  const removeField = (index: number) => {
    const next = fields.filter((_, i) => i !== index);
    // Reorder
    setFields(next.map((f, i) => ({ ...f, order: i })));
  };

  const moveField = (index: number, direction: 'up' | 'down') => {
    const next = [...fields];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= next.length) return;
    [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
    setFields(next.map((f, i) => ({ ...f, order: i })));
  };

  const buildFormData = (): CreateFormData => ({
    name,
    description: description || undefined,
    submit_button_text: submitButtonText,
    success_message: successMessage,
    redirect_url: redirectUrl || undefined,
    show_gdpr_consent: showGdpr,
    gdpr_consent_text: showGdpr ? gdprText : undefined,
    styling,
    branding,
    layout,
    fields: fields.map((f, i) => ({
      field_type: f.field_type,
      label: f.label,
      placeholder: f.placeholder || '',
      help_text: f.help_text || '',
      is_required: f.is_required,
      options: f.options || [],
      validation_rules: f.validation_rules || {},
      order: i,
      contact_field_mapping: f.contact_field_mapping === '_none' ? '' : (f.contact_field_mapping || ''),
      width: f.width || 'full',
      default_value: f.default_value || '',
      section_description: f.section_description || '',
      conditional_logic: f.conditional_logic,
    })),
  });

  const buildPreviewForm = (): Form => ({
    id: id || 'preview',
    name: name || 'Untitled Form',
    description,
    status: 'inactive',
    form_type: 'inline',
    submit_button_text: submitButtonText,
    success_message: successMessage,
    redirect_url: redirectUrl,
    show_gdpr_consent: showGdpr,
    gdpr_consent_text: gdprText,
    styling,
    branding,
    layout,
    fields: fields.map((f, i) => ({ ...f, id: f.id || `temp-${i}`, order: i })),
    submission_count: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });

  const validateStep1 = (): boolean => {
    if (!name.trim()) {
      toast.error('Form name is required');
      return false;
    }
    if (fields.length === 0) {
      toast.error('At least one field is required');
      return false;
    }
    for (const f of fields) {
      if (!f.label.trim() && f.field_type !== 'divider') {
        toast.error('All fields must have a label (except dividers)');
        return false;
      }
    }
    return true;
  };

  const handleSave = async () => {
    if (!validateStep1()) return;
    try {
      if (isEdit && id) {
        await updateForm(id, buildFormData() as UpdateFormData);
      } else {
        await createForm(buildFormData());
      }
      navigate('/forms');
    } catch {
      // Error toast is handled by the hook
    }
  };

  if (isEdit && loadingForm) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/forms')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">
            {isEdit ? 'Edit Form' : 'Create Form'}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {/* Step indicators */}
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            {steps.map((s, i) => (
              <div key={s.id} className="flex items-center">
                {i > 0 && <ChevronRight className="h-4 w-4 mx-1" />}
                <span
                  className={`cursor-pointer hover:text-foreground transition-colors ${
                    step === s.id ? 'font-semibold text-foreground' : ''
                  }`}
                  onClick={() => {
                    if (s.id === 1 || validateStep1()) setStep(s.id);
                  }}
                >
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Step 1: Fields & Settings */}
      {step === 1 && (
        <div className="grid gap-6 lg:grid-cols-5">
          {/* Left: Settings */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="p-4 space-y-4">
              <h2 className="font-semibold">Form Settings</h2>
              <div className="space-y-3">
                <div>
                  <Label>Name *</Label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="My Lead Form"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Description</Label>
                  <Textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Optional description..."
                    className="mt-1"
                    rows={2}
                  />
                </div>
                <div>
                  <Label>Submit Button Text</Label>
                  <Input
                    value={submitButtonText}
                    onChange={(e) => setSubmitButtonText(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Success Message</Label>
                  <Textarea
                    value={successMessage}
                    onChange={(e) => setSuccessMessage(e.target.value)}
                    className="mt-1"
                    rows={2}
                  />
                </div>
                <div>
                  <Label>Redirect URL (optional)</Label>
                  <Input
                    value={redirectUrl}
                    onChange={(e) => setRedirectUrl(e.target.value)}
                    placeholder="https://example.com/thank-you"
                    className="mt-1"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Leave empty to show the success message instead
                  </p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="gdpr"
                      checked={showGdpr}
                      onCheckedChange={(c) => setShowGdpr(c === true)}
                    />
                    <Label htmlFor="gdpr">Show GDPR consent checkbox</Label>
                  </div>
                  {showGdpr && (
                    <Textarea
                      value={gdprText}
                      onChange={(e) => setGdprText(e.target.value)}
                      placeholder="I agree to..."
                      rows={2}
                    />
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* Right: Fields */}
          <div className="lg:col-span-3 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Form Fields ({fields.length})</h2>
              <Button variant="outline" size="sm" onClick={() => addField()}>
                <Plus className="h-4 w-4 mr-1" /> Add Field
              </Button>
            </div>
            <div className="space-y-3">
              {fields.map((field, idx) => (
                <FormFieldEditor
                  key={field.id || idx}
                  field={field}
                  index={idx}
                  total={fields.length}
                  allFields={fields}
                  onChange={(updated) => updateField(idx, updated)}
                  onRemove={() => removeField(idx)}
                  onMoveUp={() => moveField(idx, 'up')}
                  onMoveDown={() => moveField(idx, 'down')}
                />
              ))}
              {fields.length === 0 && (
                <Card className="p-8 text-center text-muted-foreground">
                  <p>No fields yet. Click "Add Field" to get started.</p>
                </Card>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => navigate('/forms')}>
                Cancel
              </Button>
              <Button
                onClick={() => {
                  if (validateStep1()) setStep(2);
                }}
              >
                Next: Design
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Design */}
      {step === 2 && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 mb-4">
            <Button variant="outline" size="sm" onClick={() => setStep(1)}>
              <ChevronLeft className="h-4 w-4 mr-1" /> Back to Fields
            </Button>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Design Panel */}
            <div>
              <h2 className="font-semibold mb-3 flex items-center gap-2">
                <Palette className="h-4 w-4" /> Design & Styling
              </h2>
              <FormDesignPanel
                styling={styling}
                branding={branding}
                layout={layout}
                onStylingChange={setStyling}
                onBrandingChange={setBranding}
                onLayoutChange={setLayout}
              />
            </div>

            {/* Live Preview */}
            <div>
              <h2 className="font-semibold mb-3 flex items-center gap-2">
                <Eye className="h-4 w-4" /> Live Preview
              </h2>
              <div className="sticky top-6">
                <FormPreview form={buildPreviewForm()} />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button onClick={() => setStep(3)}>
              Next: Publish
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Preview & Publish */}
      {step === 3 && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 mb-4">
            <Button variant="outline" size="sm" onClick={() => setStep(2)}>
              <ChevronLeft className="h-4 w-4 mr-1" /> Back to Design
            </Button>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Preview */}
            <div>
              <h2 className="font-semibold mb-3 flex items-center gap-2">
                <Eye className="h-4 w-4" /> Final Preview
              </h2>
              <FormPreview form={buildPreviewForm()} />
            </div>

            {/* Publish actions */}
            <div className="space-y-4">
              <Card className="p-4 space-y-4">
                <h2 className="font-semibold">Publish</h2>
                <p className="text-sm text-muted-foreground">
                  Save your form, then activate it to make it publicly accessible.
                  You can get the embed code or share link from the form detail page.
                </p>
                <div className="flex flex-col gap-2">
                  <Button
                    onClick={handleSave}
                    disabled={isCreating || isUpdating}
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {isCreating || isUpdating ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Form'}
                  </Button>
                  {isEdit && (
                    <Button
                      variant="outline"
                      onClick={() => setEmbedDialogOpen(true)}
                    >
                      <Eye className="h-4 w-4 mr-2" /> Embed & Share
                    </Button>
                  )}
                </div>
              </Card>

              <Card className="p-4 space-y-2">
                <h3 className="font-medium text-sm">Summary</h3>
                <div className="text-sm space-y-1 text-muted-foreground">
                  <p>Name: <span className="text-foreground">{name}</span></p>
                  <p>Fields: <span className="text-foreground">{fields.length}</span></p>
                  <p>Layout: <span className="text-foreground">{layout.columns} column{layout.columns > 1 ? 's' : ''}</span></p>
                  <p>GDPR: <span className="text-foreground">{showGdpr ? 'Enabled' : 'Disabled'}</span></p>
                  <p>
                    After submit:{' '}
                    <span className="text-foreground">
                      {redirectUrl ? 'Redirect' : 'Show success message'}
                    </span>
                  </p>
                </div>
              </Card>

              <Card className="p-4 space-y-2">
                <h3 className="font-medium text-sm">Design Summary</h3>
                <div className="text-sm space-y-1 text-muted-foreground">
                  <p>
                    Primary Color:{' '}
                    <span className="inline-flex items-center gap-1">
                      <span
                        className="w-3 h-3 rounded-sm border"
                        style={{ backgroundColor: styling.primaryColor }}
                      />
                      <span className="text-foreground font-mono text-xs">{styling.primaryColor}</span>
                    </span>
                  </p>
                  <p>Font: <span className="text-foreground">{styling.fontFamily.split(',')[0]}</span></p>
                  <p>Max Width: <span className="text-foreground">{layout.maxWidth}</span></p>
                  {branding.headerText && <p>Header: <span className="text-foreground">{branding.headerText}</span></p>}
                  {branding.logoUrl && <p>Logo: <span className="text-foreground">Configured</span></p>}
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}

      {/* Embed dialog */}
      {isEdit && (
        <EmbedCodeDialog
          formId={id || null}
          open={embedDialogOpen}
          onOpenChange={setEmbedDialogOpen}
        />
      )}
    </div>
  );
};
