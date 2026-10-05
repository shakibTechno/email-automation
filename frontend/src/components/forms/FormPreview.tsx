import { Card } from '@/components/ui/card';
import { PublicFormRenderer } from './PublicFormRenderer';
import { Form, defaultFormStyling, defaultFormLayout } from '@/types/form';

interface FormPreviewProps {
  form: Form;
}

export const FormPreview = ({ form }: FormPreviewProps) => {
  const styling = { ...defaultFormStyling, ...form.styling };
  const layout = { ...defaultFormLayout, ...form.layout };

  return (
    <Card className="overflow-hidden">
      {/* Preview container with form's background color */}
      <div
        className="p-4"
        style={{
          backgroundColor: styling.backgroundColor === '#ffffff' ? '#f9fafb' : '#ffffff',
          minHeight: '200px',
        }}
      >
        <div
          style={{
            maxWidth: layout.maxWidth,
            margin: layout.alignment === 'center' ? '0 auto' : layout.alignment === 'right' ? '0 0 0 auto' : '0',
          }}
        >
          <PublicFormRenderer
            form={form}
            onSubmit={() => {}}
            readOnly
          />
        </div>
      </div>
    </Card>
  );
};
