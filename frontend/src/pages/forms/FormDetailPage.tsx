import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Pencil,
  Copy,
  Trash2,
  Code,
  ToggleLeft,
  ToggleRight,
  FileDown,
  FileText,
  Inbox,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FormStatusBadge } from '@/components/forms/FormStatusBadge';
import { FormPreview } from '@/components/forms/FormPreview';
import { EmbedCodeDialog } from '@/components/forms/EmbedCodeDialog';
import { SubmissionDetailDialog } from '@/components/forms/SubmissionDetailDialog';
import { useForm, useForms } from '@/hooks/useForms';
import { useFormSubmissions, useExportSubmissions } from '@/hooks/useFormSubmissions';
import { formatDate, formatDateTime } from '@/lib/utils';

export const FormDetailPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const { form, isLoading } = useForm(id || '');
  const { deleteForm, duplicateForm, toggleFormStatus } = useForms();

  const [submissionsPage, setSubmissionsPage] = useState(1);
  const {
    submissions,
    total: submissionsTotal,
    totalPages: submissionsTotalPages,
    isLoading: loadingSubmissions,
  } = useFormSubmissions(id || '', { page: submissionsPage, page_size: 20 });
  const { exportSubmissions, isExporting } = useExportSubmissions();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [embedDialogOpen, setEmbedDialogOpen] = useState(false);
  const [selectedSubmission, setSelectedSubmission] = useState<string | null>(null);
  const [submissionDialogOpen, setSubmissionDialogOpen] = useState(false);

  const handleDelete = () => {
    if (id) {
      deleteForm(id);
      navigate('/forms');
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!form) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">Form not found.</p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => navigate('/forms')}
        >
          Back to Forms
        </Button>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/forms')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{form.name}</h1>
              <FormStatusBadge status={form.status} />
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Created {formatDate(form.created_at)}
              {form.created_by_name && ` by ${form.created_by_name}`}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => id && toggleFormStatus(id)}
          >
            {form.status === 'active' ? (
              <>
                <ToggleLeft className="h-4 w-4 mr-2" /> Deactivate
              </>
            ) : (
              <>
                <ToggleRight className="h-4 w-4 mr-2" /> Activate
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setEmbedDialogOpen(true)}
          >
            <Code className="h-4 w-4 mr-2" /> Embed
          </Button>
          <Button
            size="sm"
            onClick={() => navigate(`/forms/${id}/edit`)}
          >
            <Pencil className="h-4 w-4 mr-2" /> Edit
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => id && duplicateForm(id)}
          >
            <Copy className="h-4 w-4 mr-2" /> Duplicate
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setDeleteDialogOpen(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" /> Delete
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">
            <FileText className="h-4 w-4 mr-1" /> Overview
          </TabsTrigger>
          <TabsTrigger value="submissions">
            <Inbox className="h-4 w-4 mr-1" /> Submissions ({form.submission_count})
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6 mt-4">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Form Info */}
            <Card className="p-5 space-y-4">
              <h2 className="font-semibold">Form Info</h2>
              <div className="space-y-3 text-sm">
                {form.description && (
                  <div>
                    <span className="text-muted-foreground">Description:</span>{' '}
                    {form.description}
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">Type:</span>{' '}
                  <span className="capitalize">{form.form_type.replace('_', ' ')}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Submit button:</span>{' '}
                  {form.submit_button_text}
                </div>
                <div>
                  <span className="text-muted-foreground">Submissions:</span>{' '}
                  <span className="font-medium">{form.submission_count}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">GDPR:</span>{' '}
                  {form.show_gdpr_consent ? 'Enabled' : 'Disabled'}
                </div>
                {form.redirect_url && (
                  <div>
                    <span className="text-muted-foreground">Redirect URL:</span>{' '}
                    <a
                      href={form.redirect_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      {form.redirect_url}
                      <ExternalLink className="h-3 w-3 inline ml-1" />
                    </a>
                  </div>
                )}
                {form.assign_tags && form.assign_tags.length > 0 && (
                  <div>
                    <span className="text-muted-foreground">Auto-assign tags:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {form.assign_tags.map((tag) => (
                        <Badge key={tag.id} variant="outline" className="text-xs">
                          {tag.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* Fields */}
            <Card className="p-5 space-y-4">
              <h2 className="font-semibold">Fields ({form.fields?.length || 0})</h2>
              <div className="space-y-2">
                {(form.fields || [])
                  .sort((a, b) => a.order - b.order)
                  .map((field, idx) => (
                    <div
                      key={field.id || idx}
                      className="flex items-center justify-between text-sm p-2 rounded border"
                    >
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs capitalize">
                          {field.field_type}
                        </Badge>
                        <span className="font-medium">{field.label}</span>
                        {field.is_required && (
                          <span className="text-destructive text-xs">*</span>
                        )}
                      </div>
                      {field.contact_field_mapping && (
                        <span className="text-xs text-muted-foreground">
                          → {field.contact_field_mapping}
                        </span>
                      )}
                    </div>
                  ))}
              </div>
            </Card>
          </div>

          {/* Preview */}
          <div>
            <h2 className="font-semibold mb-3">Form Preview</h2>
            <FormPreview form={form} />
          </div>
        </TabsContent>

        {/* Submissions Tab */}
        <TabsContent value="submissions" className="space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">
              Submissions ({submissionsTotal})
            </h2>
            {submissionsTotal > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => id && exportSubmissions(id)}
                disabled={isExporting}
              >
                <FileDown className="h-4 w-4 mr-2" />
                {isExporting ? 'Exporting...' : 'Export CSV'}
              </Button>
            )}
          </div>

          {loadingSubmissions ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
            </div>
          ) : submissions.length === 0 ? (
            <Card className="p-8 text-center text-muted-foreground">
              <Inbox className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No submissions yet.</p>
              <p className="text-xs mt-1">
                Submissions will appear here when visitors fill out your form.
              </p>
            </Card>
          ) : (
            <>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-secondary/50 border-b">
                    <tr>
                      <th className="text-left px-4 py-2 font-medium text-muted-foreground">
                        Contact
                      </th>
                      <th className="text-left px-4 py-2 font-medium text-muted-foreground">
                        Email
                      </th>
                      <th className="text-left px-4 py-2 font-medium text-muted-foreground">
                        GDPR
                      </th>
                      <th className="text-left px-4 py-2 font-medium text-muted-foreground">
                        Submitted
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {submissions.map((sub) => (
                      <tr
                        key={sub.id}
                        className="hover:bg-secondary/50 cursor-pointer"
                        onClick={() => {
                          setSelectedSubmission(sub.id);
                          setSubmissionDialogOpen(true);
                        }}
                      >
                        <td className="px-4 py-2">
                          {sub.contact_name || '-'}
                        </td>
                        <td className="px-4 py-2 text-muted-foreground">
                          {sub.contact_email || '-'}
                        </td>
                        <td className="px-4 py-2">
                          <Badge variant="outline" className="text-xs">
                            {sub.gdpr_consent_given ? 'Yes' : 'No'}
                          </Badge>
                        </td>
                        <td className="px-4 py-2 text-muted-foreground">
                          {formatDateTime(sub.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {submissionsTotalPages > 1 && (
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    Page {submissionsPage} of {submissionsTotalPages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSubmissionsPage((p) => p - 1)}
                      disabled={submissionsPage === 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSubmissionsPage((p) => p + 1)}
                      disabled={submissionsPage === submissionsTotalPages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Form</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{form.name}"? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Embed Dialog */}
      <EmbedCodeDialog
        formId={id || null}
        open={embedDialogOpen}
        onOpenChange={setEmbedDialogOpen}
      />

      {/* Submission Detail Dialog */}
      <SubmissionDetailDialog
        formId={id || ''}
        submissionId={selectedSubmission}
        open={submissionDialogOpen}
        onOpenChange={setSubmissionDialogOpen}
      />
    </div>
  );
};
