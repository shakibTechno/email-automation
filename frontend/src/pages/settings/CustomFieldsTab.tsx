import { useState } from 'react';
import { AlertTriangle, Pencil, Plus, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useCustomFields, useCustomFieldActions } from '@/hooks/useCustomFields';
import type { CustomField, CustomFieldType } from '@/types/contact';

const FIELD_TYPES: Array<{ value: CustomFieldType; label: string; hint: string }> = [
  { value: 'text', label: 'Text', hint: 'Any short text.' },
  { value: 'number', label: 'Number', hint: 'Comparable with greater/less than in segments.' },
  { value: 'date', label: 'Date', hint: 'Comparable by date in segments.' },
  { value: 'boolean', label: 'Yes / No', hint: 'True or false.' },
  { value: 'dropdown', label: 'Dropdown', hint: 'One value from a list you define.' },
  { value: 'multiselect', label: 'Multi-select', hint: 'Several values from a list.' },
  { value: 'url', label: 'URL', hint: 'Checked for a valid web address.' },
  { value: 'email', label: 'Email', hint: 'Checked for a valid email address.' },
];

const CHOICE_TYPES: CustomFieldType[] = ['dropdown', 'multiselect'];

interface EditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Absent for a new field. */
  field?: CustomField;
}

const FieldEditor = ({ open, onOpenChange, field }: EditorProps) => {
  const { create, update, isBusy } = useCustomFieldActions();
  const [name, setName] = useState(field?.name ?? '');
  const [type, setType] = useState<CustomFieldType>(field?.field_type ?? 'text');
  const [required, setRequired] = useState(field?.is_required ?? false);
  const [helpText, setHelpText] = useState(field?.help_text ?? '');
  const [choices, setChoices] = useState((field?.dropdown_options ?? []).join('\n'));

  const needsChoices = CHOICE_TYPES.includes(type);
  const parsedChoices = choices
    .split('\n')
    .map((c) => c.trim())
    .filter(Boolean);

  const blocked =
    !name.trim() || isBusy || (needsChoices && parsedChoices.length === 0);

  const submit = () => {
    const payload: Partial<CustomField> = {
      name: name.trim(),
      field_type: type,
      is_required: required,
      help_text: helpText.trim(),
      dropdown_options: needsChoices ? parsedChoices : [],
    };

    if (field) {
      update.mutate(
        { id: field.id, payload },
        { onSuccess: () => onOpenChange(false) }
      );
    } else {
      create.mutate(payload, { onSuccess: () => onOpenChange(false) });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[15px]">
            {field ? `Edit ${field.name}` : 'Add a custom field'}
          </DialogTitle>
          <DialogDescription className="text-[12.5px]">
            Custom fields appear on every contact, in the import mapper and in the
            segment rule builder.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3.5">
          <div className="space-y-1.5">
            <Label htmlFor="cf-name" className="text-[12.5px]">
              Name
            </Label>
            <Input
              id="cf-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Industry"
            />
            {/* The key is what values are stored under and never changes, which
                is what makes renaming safe — worth saying, because the opposite
                used to be true and renaming orphaned the data. */}
            {field && (
              <p className="text-[11.5px] text-muted-foreground">
                Stored as <span className="font-mono">{field.key}</span>. Renaming is
                safe — the stored key does not change, so existing values stay
                attached.
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label className="text-[12.5px]">Type</Label>
            <Select
              value={type}
              onValueChange={(v) => setType(v as CustomFieldType)}
              disabled={!!field}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FIELD_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11.5px] text-muted-foreground">
              {field
                ? 'The type cannot change once contacts hold values in this field.'
                : FIELD_TYPES.find((t) => t.value === type)?.hint}
            </p>
          </div>

          {needsChoices && (
            <div className="space-y-1.5">
              <Label htmlFor="cf-choices" className="text-[12.5px]">
                Choices
              </Label>
              <textarea
                id="cf-choices"
                value={choices}
                onChange={(e) => setChoices(e.target.value)}
                rows={4}
                placeholder={'gold\nsilver\nbronze'}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-[12.5px] ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <p className="text-[11.5px] text-muted-foreground">
                One per line. A value outside this list is refused.
              </p>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="cf-help" className="text-[12.5px]">
              Help text
            </Label>
            <Input
              id="cf-help"
              value={helpText}
              onChange={(e) => setHelpText(e.target.value)}
              placeholder="Shown under the field on a contact"
            />
          </div>

          <label className="flex items-start gap-2 text-[12.5px]">
            <Checkbox
              checked={required}
              onCheckedChange={(v) => setRequired(v === true)}
              className="mt-0.5"
            />
            <span>
              Required
              <span className="block text-[11.5px] text-muted-foreground">
                New contacts cannot be created without it. Existing contacts are
                unaffected.
              </span>
            </span>
          </label>
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} disabled={blocked}>
            {isBusy ? 'Saving…' : field ? 'Save changes' : 'Add field'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export function CustomFieldsTab() {
  const { fields, isLoading } = useCustomFields();
  const { remove } = useCustomFieldActions();
  const [editing, setEditing] = useState<CustomField | undefined>();
  const [adding, setAdding] = useState(false);
  const [deleting, setDeleting] = useState<CustomField | undefined>();

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[15px] font-semibold">Custom fields</h2>
          <p className="text-[13px] text-muted-foreground">
            Anything you track about a contact that the standard fields do not
            cover. They appear on every contact, in the import mapper and in segment
            rules.
          </p>
        </div>
        <Button size="sm" onClick={() => setAdding(true)}>
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Add field
        </Button>
      </div>

      <div className="overflow-hidden rounded-lg border bg-card shadow-card">
        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-11 w-full rounded-md" />
            ))}
          </div>
        ) : fields.length === 0 ? (
          <div className="px-4 py-14 text-center">
            <h3 className="mb-1 text-[14px] font-semibold">No custom fields yet</h3>
            <p className="text-[12.5px] text-muted-foreground">
              Add one for anything you need to store that is not a standard contact
              field.
            </p>
          </div>
        ) : (
          <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-full">Field</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Required</TableHead>
                  <TableHead className="text-right">In use</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {fields.map((field) => (
                  <TableRow key={field.id}>
                    <TableCell>
                      <span className="text-[13px] font-medium">{field.name}</span>
                      <span className="ml-2 font-mono text-[11px] text-subtle-foreground">
                        {field.key}
                      </span>
                      {field.help_text && (
                        <span className="block text-[11.5px] text-muted-foreground">
                          {field.help_text}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-[12.5px]">
                      {FIELD_TYPES.find((t) => t.value === field.field_type)?.label ??
                        field.field_type}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-[12.5px]">
                      {field.is_required ? 'Yes' : '—'}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums">
                      {field.contact_count}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => setEditing(field)}
                          title="Edit"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                          onClick={() => setDeleting(field)}
                          title="Remove"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {adding && <FieldEditor open onOpenChange={() => setAdding(false)} />}
      {editing && (
        <FieldEditor
          key={editing.id}
          open
          onOpenChange={() => setEditing(undefined)}
          field={editing}
        />
      )}

      <AlertDialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(undefined)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {deleting?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              {/* The count is the point. "Remove this field" reads very
                  differently at 0 contacts and at 4,000. */}
              {deleting?.contact_count
                ? `${deleting.contact_count} contact${
                    deleting.contact_count === 1 ? '' : 's'
                  } hold a value for this field. The definition is removed and those
                  values stop being shown or usable in segments.`
                : 'No contacts hold a value for this field yet.'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleting && remove.mutate(deleting.id)}
            >
              Remove field
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {fields.some((f) => f.contact_count > 0) && (
        <p className="flex items-start gap-1.5 text-[11.5px] text-muted-foreground">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-none" />
          A field's type cannot be changed once contacts hold values in it — the
          stored values would no longer match it. Add a new field instead.
        </p>
      )}
    </div>
  );
}
