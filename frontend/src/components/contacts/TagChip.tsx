import { cn } from '@/lib/utils';
import { tagColorHex } from '@/lib/tagColors';
import type { Tag } from '@/types/contact';

interface TagChipProps {
  tag: Pick<Tag, 'name' | 'color'>;
  size?: 'sm' | 'md';
  onRemove?: () => void;
  className?: string;
}

/**
 * Tags carry a colour the user picked, which has to survive — but painting a
 * saturated fill with white text made every tag fight the palette and go
 * illegible on a pale colour. The chip is a neutral palette surface and the
 * user's colour becomes the dot, so the hue still identifies the tag without
 * competing with the status badges beside it.
 *
 * The dot resolves through `tagColorHex` because the stored value is a name
 * like `blue`, which CSS would otherwise paint as its own shouting primary.
 */
export const TagChip = ({ tag, size = 'md', onRemove, className }: TagChipProps) => (
  <span
    className={cn(
      'inline-flex max-w-full items-center gap-1.5 rounded-[5px] border bg-secondary font-medium text-foreground',
      size === 'sm' ? 'px-1.5 py-0.5 text-[10.5px]' : 'px-2 py-0.5 text-[11.5px]',
      className
    )}
  >
    <span
      className="h-2 w-2 flex-none rounded-full"
      style={{ backgroundColor: tagColorHex(tag.color) }}
      aria-hidden="true"
    />
    <span className="truncate">{tag.name}</span>
    {onRemove && (
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove tag ${tag.name}`}
        className="ml-0.5 flex-none text-subtle-foreground hover:text-destructive"
      >
        ×
      </button>
    )}
  </span>
);
