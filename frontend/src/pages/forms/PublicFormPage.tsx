import { useSearchParams, useParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { PublicFormRenderer } from '@/components/forms/PublicFormRenderer';
import { usePublicForm, useSubmitForm } from '@/hooks/usePublicForm';
import { CheckCircle2 } from 'lucide-react';
import { defaultFormStyling, defaultFormLayout } from '@/types/form';

/**
 * Tell the page that framed us what happened.
 *
 * `targetOrigin` is '*' on purpose and is safe here because nothing sensitive
 * is sent: a form id, a flag, and a redirect URL the customer configured. The
 * submitted email deliberately never crosses this boundary -- every script on
 * the host page can listen for `message`, including their ad tech -- so the
 * contact is matched server-side from the submission itself.
 */
function notifyParent(message: Record<string, unknown>) {
  if (window.parent === window) return;
  try {
    window.parent.postMessage({ source: 'mailflow-form', ...message }, '*');
  } catch {
    // A parent that refuses messages is not our problem to solve.
  }
}

export const PublicFormPage = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  // Embedded in a popup: no page chrome, no full-height centring, and the
  // parent owns navigation.
  const embed = searchParams.get('embed') === '1';

  const { form, isLoading, error } = usePublicForm(id || '');
  const { submitForm, isSubmitting, isSuccess, data: submitResponse } = useSubmitForm(id || '');

  const handleSubmit = async (values: Record<string, any>, gdprConsent: boolean) => {
    try {
      const response = await submitForm({
        data: values,
        gdpr_consent_given: gdprConsent,
        source_url: window.location.href,
      });

      if (embed) {
        // Redirecting here would load the customer's thank-you page inside a
        // 400px modal. The parent navigates its own top-level document.
        notifyParent({
          type: 'submitted',
          formId: id,
          redirectUrl: response.redirect_url || null,
        });
        return;
      }

      if (response.redirect_url) {
        window.location.href = response.redirect_url;
      }
    } catch {
      // Error is handled by the hook
    }
  };

  // `min-h-screen` is 100% of the *iframe*, which is why the embedded form
  // cannot be laid out like the standalone page: the content would always
  // grow to whatever height the frame was given.
  const shellClass = embed
    ? 'flex items-start justify-center p-3'
    : 'min-h-screen flex items-center justify-center p-4';

  if (isLoading) {
    return (
      <div className={`${shellClass} ${embed ? '' : 'bg-secondary/50'}`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error || !form) {
    return (
      <div className={`${shellClass} ${embed ? '' : 'bg-secondary/50'}`}>
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

  // The popup draws its own surface, so a second background behind the form
  // renders as a visible gutter inside the modal.
  const shellStyle = embed
    ? { backgroundColor: 'transparent' }
    : {
        backgroundColor:
          styling.backgroundColor === '#ffffff' ? '#f9fafb' : styling.backgroundColor,
      };

  if (isSuccess && !submitResponse?.redirect_url) {
    return (
      <div className={shellClass} style={shellStyle}>
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
    <div className={shellClass} style={shellStyle}>
      <PublicFormRenderer
        form={form}
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
      />
    </div>
  );
};
