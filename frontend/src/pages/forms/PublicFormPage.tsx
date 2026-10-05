import { useParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { PublicFormRenderer } from '@/components/forms/PublicFormRenderer';
import { usePublicForm, useSubmitForm } from '@/hooks/usePublicForm';
import { CheckCircle2 } from 'lucide-react';
import { defaultFormStyling, defaultFormLayout } from '@/types/form';

export const PublicFormPage = () => {
  const { id } = useParams<{ id: string }>();
  const { form, isLoading, error } = usePublicForm(id || '');
  const { submitForm, isSubmitting, isSuccess, data: submitResponse } = useSubmitForm(id || '');

  const handleSubmit = async (values: Record<string, any>, gdprConsent: boolean) => {
    try {
      const response = await submitForm({
        data: values,
        gdpr_consent_given: gdprConsent,
        source_url: window.location.href,
      });

      // Handle redirect if provided
      if (response.redirect_url) {
        window.location.href = response.redirect_url;
      }
    } catch {
      // Error is handled by the hook
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error || !form) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Card className="p-8 text-center max-w-md">
          <h2 className="text-xl font-semibold mb-2">Form Not Available</h2>
          <p className="text-muted-foreground">
            This form is either inactive or does not exist.
          </p>
        </Card>
      </div>
    );
  }

  // Get styling from form or use defaults
  const styling = { ...defaultFormStyling, ...form.styling };
  const layout = { ...defaultFormLayout, ...form.layout };

  if (isSuccess && !submitResponse?.redirect_url) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-4"
        style={{ backgroundColor: styling.backgroundColor === '#ffffff' ? '#f9fafb' : styling.backgroundColor }}
      >
        <Card
          className="p-8 text-center"
          style={{
            maxWidth: layout.maxWidth,
            backgroundColor: styling.backgroundColor,
            fontFamily: styling.fontFamily,
          }}
        >
          <CheckCircle2
            className="h-12 w-12 mx-auto mb-4"
            style={{ color: styling.successColor }}
          />
          <h2
            className="text-xl font-semibold mb-2"
            style={{ color: styling.textColor }}
          >
            Thank You!
          </h2>
          <p style={{ color: styling.labelColor }}>
            {submitResponse?.message || form.success_message || 'Your submission has been received.'}
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        backgroundColor: styling.backgroundColor === '#ffffff' ? '#f9fafb' : styling.backgroundColor,
      }}
    >
      <PublicFormRenderer
        form={form}
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
      />
    </div>
  );
};
