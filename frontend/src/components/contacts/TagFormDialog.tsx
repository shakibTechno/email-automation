import { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { TagChip } from '@/components/contacts/TagChip';
import { TAG_COLORS, DEFAULT_TAG_COLOR } from '@/lib/tagColors';
import { cn } from '@/lib/utils';
import type { CreateTagData, Tag } from '@/types/contact';

/** `Tag.name` is a CharField(max_length=50); the counter keeps that visible. */
const NAME_LIMIT = 50;

interface TagFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Absent means create. */
  tag?: Tag | null;
  onSubmit: (data: CreateTagData) => void;
  isSubmitting?: boolean;
  /** Names already taken, so the clash is caught before the round trip. */
  existingNames?: string[];
}

/**
 * Create and edit were two near-identical copies of this form, which is how
 * they drifted — only one of them had the preview in the right place. One
 * dialog serves both, seeded from `tag` when editing.
 */
export const TagFormDialog = ({
  open,
  onOpenChange,
  tag,
  onSubmit,
  isSubmitting,
  existingNames = [],
}: TagFormDialogProps) => {
  const [name, setName] = useState('');
  const [color, setColor] = useState<string>(DEFAULT_TAG_COLOR);
  const [description, setDescription] = useState('');

  // Reseed on open rather than on mount: the dialog stays mounted between
  // edits, so mount-time state would show the previously edited tag.
  useEffect(() => {
    if (!open) return;
    setName(tag?.name ?? '');
    setColor(tag?.color ?? DEFAULT_TAG_COLOR);
    setDescription(tag?.description ?? '');
  }, [open, tag]);

  const trimmed = name.trim();
  const isDuplicate = existingNames.some(
    (existing) => existing.toLowerCase() === trimmed.toLowerCase()
  );
  const canSubmit = trimmed.length > 0 && trimmed.length <= NAME_LIMIT && !isDuplicate;

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit({ name: trimmed, color, description: description.trim() });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[460px]">
        <DialogHeader>
          <DialogTitle>{tag ? 'Edit tag' : 'New tag'}</DialogTitle>
          <DialogDescription>
            {tag
              ? 'Renaming a tag updates it everywhere it is already applied.'
              : 'Tags group contacts so you can segment and target them later.'}
          </DialogDescription>
        </DialogHeader>

        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
        >
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between">
              <Label htmlFor="tag-name">Name</Label>
              <span
                className={cn(
                  'font-mono text-[10.5px] text-subtle-foreground',
                  trimmed.length > NAME_LIMIT && 'text-destructive'
                )}
              >
                {trimmed.length}/{NAME_LIMIT}
              </span>
            </div>
            <Input
              id="tag-name"
              autoFocus
              placeholder="Newsletter, VIP, Trade show…"
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-invalid={isDuplicate || trimmed.length > NAME_LIMIT}
            />
            {isDuplicate && (
              <p className="text-[12px] text-destructive">
                A tag called “{trimmed}” already exists.
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label>Colour</Label>
            <div className="flex flex-wrap gap-1.5">
              {TAG_COLORS.map((option) => {
                const selected = color === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    title={option.label}
                    aria-label={option.label}
                    aria-pressed={selected}
                    onClick={() => setColor(option.value)}
                    className={cn(
                      'flex h-7 w-7 items-center justify-center rounded-full ring-offset-2 ring-offset-card transition-shadow',
                      selected && 'ring-2 ring-foreground'
                    )}
                    style={{ backgroundColor: option.hex }}
                  >
                    {selected && <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="tag-description">
              Description <span className="text-subtle-foreground">(optional)</span>
            </Label>
            <Textarea
              id="tag-description"
              rows={2}
              placeholder="What earns a contact this tag?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {/* The colour only means anything as the chip the user will actually
              see on a contact row, so the preview shows that exact component. */}
          <div className="flex items-center gap-2.5 rounded-md border border-dashed bg-secondary/40 px-3 py-2.5">
            <span className="eyebrow">Preview</span>
            <TagChip tag={{ name: trimmed || 'Tag name', color }} />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!canSubmit || isSubmitting}>
              {isSubmitting ? 'Saving…' : tag ? 'Save changes' : 'Create tag'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
