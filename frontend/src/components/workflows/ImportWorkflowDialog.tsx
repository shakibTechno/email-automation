import { DragEvent, useState } from 'react';
import { Upload, AlertTriangle, FileJson } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { workflowsApi } from '@/api/workflows';
import { WorkflowImportReport } from '@/types/workflow';

/**
 * Bring a workflow in from an exported file.
 *
 * The result is always a draft, and the report afterwards is the point: a
 * workflow from another account references tags, templates and segments by
 * ids that mean nothing here, so anything the server could not match by name
 * has been cleared and is listed. Activating before fixing those would give a
 * workflow that fails the moment a contact reaches the step.
 */

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported: (workflowId: string) => void;
}

const MAX_BYTES = 2 * 1024 * 1024;

export default function ImportWorkflowDialog({
  open, onOpenChange, onImported,
}: Props) {
  const [fileName, setFileName] = useState('');
  const [definition, setDefinition] = useState<unknown>(null);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<WorkflowImportReport | null>(null);
  const [importedId, setImportedId] = useState('');

  const reset = () => {
    setFileName('');
    setDefinition(null);
    setName('');
    setError('');
    setReport(null);
    setImportedId('');
  };

  const readFile = async (file: File) => {
    setError('');
    setReport(null);

    if (file.size > MAX_BYTES) {
      setError('That file is larger than 2 MB, so it is not a workflow export.');
      return;
    }
    try {
      const parsed = JSON.parse(await file.text());
      setDefinition(parsed);
      setFileName(file.name);
      // Offer the exported name, editable: importing the same flow twice is
      // normal and two rows with identical names are hard to tell apart.
      const exported = (parsed as { workflow?: { name?: string } })?.workflow?.name;
      setName(exported || file.name.replace(/\.(workflow\.)?json$/i, ''));
    } catch {
      setError('That file is not readable JSON.');
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) void readFile(file);
  };

  const handleImport = async () => {
    if (!definition) return;
    setBusy(true);
    setError('');
    try {
      const result = await workflowsApi.importWorkflow(definition, name.trim());
      setReport(result.report);
      setImportedId(result.workflow.id);
      toast.success('Workflow imported as a draft');
    } catch (e: any) {
      setError(
        e?.response?.data?.detail || e?.message || 'The workflow could not be imported.',
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Import a workflow</DialogTitle>
          <DialogDescription>
            Upload a workflow exported from this platform. It arrives as a
            draft so you can check it before anything is sent.
          </DialogDescription>
        </DialogHeader>

        {report ? (
          <div className="space-y-3">
            <p className="text-sm">
              Imported {report.nodes_created} step
              {report.nodes_created === 1 ? '' : 's'} and{' '}
              {report.edges_created} connection
              {report.edges_created === 1 ? '' : 's'}.
            </p>

            {report.unresolved.length > 0 ? (
              <div className="rounded-md border border-warning/40 bg-warning/[.08] p-3">
                <p className="flex items-center gap-2 text-sm font-medium">
                  <AlertTriangle className="h-4 w-4 text-warning" />
                  {report.unresolved.length} reference
                  {report.unresolved.length === 1 ? '' : 's'} could not be matched
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  These existed in the account the workflow came from and have no
                  match here. The steps that used them need setting up before you
                  activate it.
                </p>
                <ul className="mt-2 space-y-1 text-xs">
                  {report.unresolved.slice(0, 8).map((item, index) => (
                    <li key={index}>
                      <span className="font-medium">{item.node || 'A step'}</span>
                      {' wanted the '}
                      {item.kind.replace(/_/g, ' ')}
                      {' '}
                      &ldquo;{item.name}&rdquo;
                    </li>
                  ))}
                  {report.unresolved.length > 8 && (
                    <li className="text-muted-foreground">
                      and {report.unresolved.length - 8} more
                    </li>
                  )}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-success">
                Every reference was matched in this account.
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div
              onDrop={handleDrop}
              onDragOver={(event) => event.preventDefault()}
              className="rounded-lg border-2 border-dashed p-6 text-center"
            >
              {fileName ? (
                <p className="flex items-center justify-center gap-2 text-sm">
                  <FileJson className="h-4 w-4" />
                  {fileName}
                </p>
              ) : (
                <>
                  <Upload className="mx-auto h-6 w-6 text-muted-foreground" />
                  <p className="mt-2 text-sm text-muted-foreground">
                    Drop a <code>.workflow.json</code> file here
                  </p>
                </>
              )}
              <Input
                type="file"
                accept="application/json,.json"
                className="mt-3"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void readFile(file);
                }}
              />
            </div>

            {definition != null && (
              <div>
                <Label htmlFor="import-name">Name</Label>
                <Input
                  id="import-name"
                  className="mt-1"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </div>
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        )}

        <DialogFooter>
          {report ? (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Close
              </Button>
              <Button onClick={() => onImported(importedId)}>
                Open the workflow
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleImport} disabled={!definition || busy}>
                {busy ? 'Importing…' : 'Import'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
