import { useEffect, useState } from 'react';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FileText, Megaphone, Loader2 } from 'lucide-react';
import { usePopupTemplates, usePopups } from '@/hooks/usePopups';
import { popupTypeLabels, PopupTemplate } from '@/types/popup';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (id: string) => void;
}

export const PopupTemplateDialog = ({ open, onOpenChange, onCreated }: Props) => {
  const { data: templates = [], isLoading } = usePopupTemplates();
  const { createPopup, isCreating } = usePopups();

  const [selected, setSelected] = useState<PopupTemplate | null>(null);
  const [name, setName] = useState('');
  const [nameTouched, setNameTouched] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSelected(null);
    setName('');
    setNameTouched(false);
  }, [open]);

  // Choosing is the decision; the name is a confirmation of it. Overwriting
  // something they typed would be rude.
  useEffect(() => {
    if (!nameTouched) setName(selected?.name || '');
  }, [selected, nameTouched]);

  const create = async () => {
    const popup = await createPopup({
      name: name.trim() || selected?.name || 'Untitled pop-up',
      template_id: selected?.id ?? null,
    });
    onOpenChange(false);
    onCreated(popup.id);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>New pop-up</DialogTitle>
          <DialogDescription>
            Start from a template, or from nothing.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid max-h-[22rem] auto-rows-max grid-cols-2 content-start gap-2.5 overflow-y-auto md:grid-cols-3">
            <button
              type="button"
              onClick={() => setSelected(null)}
              aria-pressed={selected === null}
              className={`rounded-lg border p-3 text-left transition-colors ${
                selected === null ? 'border-primary ring-1 ring-primary' : 'hover:bg-secondary'
              }`}
            >
              <div className="font-medium">Blank</div>
              <p className="mt-1 text-[13px] text-muted-foreground">
                Write it yourself.
              </p>
            </button>

            {templates.map((template) => (
              <button
                key={template.id}
                type="button"
                onClick={() => setSelected(template)}
                aria-pressed={selected?.id === template.id}
                className={`rounded-lg border p-3 text-left transition-colors ${
                  selected?.id === template.id
                    ? 'border-primary ring-1 ring-primary'
                    : 'hover:bg-secondary'
                }`}
              >
                <div className="flex items-center gap-1.5 font-medium">
                  {template.wants_form ? (
                    <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                  ) : (
                    <Megaphone className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                  {template.name}
                </div>
                <p className="mt-1 text-[13px] text-muted-foreground">
                  {template.description}
                </p>
                <p className="mt-1.5 text-xs text-muted-foreground">
                  {popupTypeLabels[template.popup_type]}
                  {!template.wants_form && ' · no form'}
                </p>
              </button>
            ))}
          </div>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="popup-name">Name</Label>
          <Input
            id="popup-name"
            value={name}
            placeholder="Spring newsletter"
            onChange={(e) => { setName(e.target.value); setNameTouched(true); }}
          />
          <p className="text-xs text-muted-foreground">
            For your list only — visitors never see it.
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={create} disabled={isCreating || !name.trim()}>
            {isCreating ? 'Creating...' : 'Create'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
