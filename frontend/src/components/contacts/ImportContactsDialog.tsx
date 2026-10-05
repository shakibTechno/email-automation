import { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Upload, Download, FileText, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import Papa from 'papaparse';
import { contactsApi } from '@/api/contacts';
import { cn } from '@/lib/utils';

const CONTACT_FIELDS = [
  { value: '',          label: '(Skip column)' },
  { value: 'email',     label: 'Email (required)' },
  { value: 'first_name', label: 'First Name' },
  { value: 'last_name', label: 'Last Name' },
  { value: 'phone',     label: 'Phone' },
  { value: 'company',   label: 'Company' },
  { value: 'job_title', label: 'Job Title' },
];

const ALIASES: Record<string, string> = {
  mail: 'email', e_mail: 'email',
  firstname: 'first_name', first: 'first_name', fname: 'first_name',
  lastname: 'last_name', last: 'last_name', lname: 'last_name', surname: 'last_name',
  telephone: 'phone', tel: 'phone', mobile: 'phone',
  organization: 'company', org: 'company',
  title: 'job_title', position: 'job_title', role: 'job_title',
};

function autoMap(col: string): string {
  const key = col.toLowerCase().replace(/[\s\-.]/g, '_');
  const known = ['email', 'first_name', 'last_name', 'phone', 'company', 'job_title'];
  return ALIASES[key] ?? (known.includes(key) ? key : '');
}

const SAMPLE_CSV = [
  'email,first_name,last_name,company,phone,job_title',
  'alice@example.com,Alice,Smith,Acme Corp,+1 555-1234,CEO',
  'bob@example.com,Bob,Jones,Globex,+1 555-5678,Engineer',
].join('\n');

type Step = 'upload' | 'map' | 'results';

interface ImportResult {
  imported: number;
  updated: number;
  skipped: number;
  errors: Array<{ row: number; error: string }>;
}

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ImportContactsDialog({ open, onClose }: Props) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<Step>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [updateExisting, setUpdateExisting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);

  const importMutation = useMutation({
    mutationFn: contactsApi.importContacts,
    onSuccess: (data) => {
      setResult(data.results);
      setStep('results');
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Import failed. Please try again.');
    },
  });

  function reset() {
    setStep('upload');
    setFile(null);
    setCsvHeaders([]);
    setMapping({});
    setSkipDuplicates(true);
    setUpdateExisting(false);
    setResult(null);
  }

  function handleClose() {
    reset();
    onClose();
  }

  function processFile(f: File) {
    if (!f.name.endsWith('.csv')) {
      toast.error('Please upload a CSV file (.csv)');
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      toast.error('File must be under 5 MB');
      return;
    }
    setFile(f);
    Papa.parse(f, {
      header: true,
      preview: 1,
      complete: (res) => {
        const headers = res.meta.fields ?? [];
        setCsvHeaders(headers);
        const auto: Record<string, string> = {};
        headers.forEach((h) => { auto[h] = autoMap(h); });
        setMapping(auto);
        setStep('map');
      },
      error: () => toast.error('Could not read CSV file'),
    });
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) processFile(f);
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) processFile(f);
    e.target.value = '';
  }

  function downloadSample() {
    const blob = new Blob([SAMPLE_CSV], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'contacts_sample.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  function emailIsMapped() {
    return Object.values(mapping).includes('email');
  }

  function hasDuplicateMappings() {
    const mapped = Object.values(mapping).filter(Boolean);
    return mapped.length !== new Set(mapped).size;
  }

  function handleImport() {
    const fieldMapping: Record<string, string> = {};
    Object.entries(mapping).forEach(([col, field]) => {
      if (field) fieldMapping[col] = field;
    });
    const formData = new FormData();
    formData.append('file', file!);
    formData.append('field_mapping', JSON.stringify(fieldMapping));
    formData.append('skip_duplicates', String(skipDuplicates));
    formData.append('update_existing', String(updateExisting));
    importMutation.mutate(formData);
  }

  const stepTitles: Record<Step, string> = {
    upload: 'Import Contacts',
    map: 'Map Columns',
    results: 'Import Complete',
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(); }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{stepTitles[step]}</DialogTitle>
        </DialogHeader>

        {step === 'upload' && (
          <div className="space-y-4 py-2">
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
                dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'
              )}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm font-medium">Drop your CSV file here</p>
              <p className="text-xs text-muted-foreground mt-1">or click to browse — max 5 MB</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileInput}
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={downloadSample}
            >
              <Download className="h-4 w-4 mr-2" />
              Download sample CSV
            </Button>

            <div className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
              <span className="font-medium">Supported fields:</span>{' '}
              email (required), first_name, last_name, company, phone, job_title
            </div>
          </div>
        )}

        {step === 'map' && (
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4 shrink-0" />
              <span className="truncate font-medium text-foreground">{file?.name}</span>
              <span className="shrink-0">· {csvHeaders.length} column{csvHeaders.length !== 1 ? 's' : ''} detected</span>
            </div>

            <div className="rounded-lg border overflow-hidden">
              <div className="grid grid-cols-2 gap-0 bg-muted px-3 py-2 text-xs font-medium text-muted-foreground">
                <span>CSV column</span>
                <span>Contact field</span>
              </div>
              <div className="divide-y max-h-52 overflow-y-auto">
                {csvHeaders.map((col) => (
                  <div key={col} className="grid grid-cols-2 gap-2 items-center px-3 py-2">
                    <span className="text-sm truncate" title={col}>{col}</span>
                    <Select
                      value={mapping[col] ?? ''}
                      onValueChange={(v) => setMapping((prev) => ({ ...prev, [col]: v }))}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="(Skip)" />
                      </SelectTrigger>
                      <SelectContent>
                        {CONTACT_FIELDS.map((f) => (
                          <SelectItem key={f.value} value={f.value} className="text-xs">
                            {f.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </div>
            </div>

            {!emailIsMapped() && (
              <p className="text-xs text-destructive flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                Map at least one column to <strong>Email</strong> to continue.
              </p>
            )}
            {hasDuplicateMappings() && (
              <p className="text-xs text-destructive flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                The same contact field is mapped to multiple columns.
              </p>
            )}

            <div className="rounded-lg border p-3 space-y-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Duplicate handling</p>
              <div className="flex items-center justify-between">
                <Label htmlFor="skip-dup" className="text-sm cursor-pointer">Skip duplicate emails</Label>
                <Switch
                  id="skip-dup"
                  checked={skipDuplicates}
                  onCheckedChange={setSkipDuplicates}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="update-existing" className="text-sm cursor-pointer">Update existing contacts</Label>
                <Switch
                  id="update-existing"
                  checked={updateExisting}
                  onCheckedChange={setUpdateExisting}
                />
              </div>
            </div>
          </div>
        )}

        {step === 'results' && result && (
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg bg-success/[.10] border border-success/[.30] p-3 text-center">
                <div className="text-2xl font-bold text-success">{result.imported}</div>
                <div className="text-xs text-success mt-0.5">Imported</div>
              </div>
              <div className="rounded-lg bg-info/[.10] border border-info/[.30] p-3 text-center">
                <div className="text-2xl font-bold text-brand">{result.updated}</div>
                <div className="text-xs text-brand mt-0.5">Updated</div>
              </div>
              <div className="rounded-lg bg-muted p-3 text-center">
                <div className="text-2xl font-bold">{result.skipped}</div>
                <div className="text-xs text-muted-foreground mt-0.5">Skipped</div>
              </div>
            </div>

            {result.errors.length === 0 ? (
              <div className="flex items-center gap-2 text-sm text-success bg-success/[.10] rounded-lg p-3">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                Import completed with no errors.
              </div>
            ) : (
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-sm font-medium text-destructive">
                  <XCircle className="h-4 w-4" />
                  {result.errors.length} row{result.errors.length !== 1 ? 's' : ''} had errors
                </div>
                <div className="rounded-lg border max-h-40 overflow-y-auto divide-y text-xs">
                  {result.errors.map((e, i) => (
                    <div key={i} className="flex gap-2 px-3 py-2">
                      <span className="text-muted-foreground shrink-0">Row {e.row}</span>
                      <span className="text-destructive">{e.error}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {step === 'upload' && (
            <Button variant="outline" onClick={handleClose}>Cancel</Button>
          )}

          {step === 'map' && (
            <>
              <Button variant="outline" onClick={() => { setStep('upload'); setFile(null); }}>
                Back
              </Button>
              <Button
                onClick={handleImport}
                disabled={!emailIsMapped() || hasDuplicateMappings() || importMutation.isPending}
              >
                {importMutation.isPending ? 'Importing…' : 'Import Contacts'}
              </Button>
            </>
          )}

          {step === 'results' && (
            <>
              <Button variant="outline" onClick={reset}>Import Another</Button>
              <Button onClick={handleClose}>Done</Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
