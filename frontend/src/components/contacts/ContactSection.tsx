import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';

interface ContactSectionProps {
  title: string;
  description?: string;
  /** Open on mount — for a section that already holds values. */
  defaultOpen?: boolean;
  /** How many of this section's fields are filled, shown on the header. */
  filledCount?: number;
  children: React.ReactNode;
}

/**
 * One collapsible group of contact fields.
 *
 * The form carried eight inputs and now covers about thirty. Flat, that is a
 * wall that makes the six fields people actually fill harder to find, so the
 * additions are grouped and closed by default — except where the contact
 * already has values in them, which is the one case where hiding them would be
 * hiding data.
 */
export const ContactSection = ({
  title,
  description,
  defaultOpen = false,
  filledCount = 0,
  children,
}: ContactSectionProps) => {
  const [open, setOpen] = useState(defaultOpen || filledCount > 0);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-lg border">
      <CollapsibleTrigger className="flex w-full items-center gap-2 px-3.5 py-3 text-left hover:bg-accent/50">
        <span className="text-[13.5px] font-semibold">{title}</span>
        {filledCount > 0 && (
          <span className="rounded bg-brand/[.12] px-1.5 py-0.5 text-[11px] font-medium text-brand">
            {filledCount}
          </span>
        )}
        {description && !open && (
          <span className="truncate text-[12px] text-muted-foreground">{description}</span>
        )}
        <ChevronDown
          className={cn(
            'ml-auto h-4 w-4 flex-none text-subtle-foreground transition-transform',
            open && 'rotate-180'
          )}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-4 border-t p-3.5">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
};
