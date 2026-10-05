import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { formsApi } from '@/api/forms';
import { FormSubmission } from '@/types/form';
import { formatDateTime } from '@/lib/utils';

interface SubmissionDetailDialogProps {
  formId: string;
  submissionId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const SubmissionDetailDialog = ({
  formId,
  submissionId,
  open,
  onOpenChange,
}: SubmissionDetailDialogProps) => {
  const [submission, setSubmission] = useState<FormSubmission | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && submissionId && formId) {
      setLoading(true);
      formsApi
        .getSubmissionDetail(formId, submissionId)
        .then(setSubmission)
        .catch(() => setSubmission(null))
        .finally(() => setLoading(false));
    }
  }, [open, submissionId, formId]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Submission Details</DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
          </div>
        ) : submission ? (
          <div className="space-y-4">
            {/* Contact info */}
            {submission.contact && (
              <div className="p-3 bg-muted rounded-lg text-sm">
                <p className="font-medium">
                  {submission.contact.first_name} {submission.contact.last_name}
                </p>
                <p className="text-muted-foreground">{submission.contact.email}</p>
              </div>
            )}

            {/* Field data */}
            <div className="space-y-3">
              {(submission.data || []).map((item, idx) => (
                <div key={idx} className="text-sm">
                  <span className="text-muted-foreground">{item.label}:</span>{' '}
                  <span className="font-medium">
                    {Array.isArray(item.value) ? item.value.join(', ') : String(item.value || '-')}
                  </span>
                </div>
              ))}
            </div>

            {/* Metadata */}
            <div className="border-t pt-3 space-y-2 text-sm text-muted-foreground">
              <div>
                <span>Submitted:</span>{' '}
                {formatDateTime(submission.created_at)}
              </div>
              {submission.ip_address && (
                <div>
                  <span>IP:</span> {submission.ip_address}
                </div>
              )}
              {submission.source_url && (
                <div>
                  <span>Source:</span> {submission.source_url}
                </div>
              )}
              <div className="flex items-center gap-2">
                <span>GDPR Consent:</span>
                <Badge variant="outline" className="text-xs">
                  {submission.gdpr_consent_given ? 'Yes' : 'No'}
                </Badge>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-center text-muted-foreground py-4">
            Submission not found.
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
};
