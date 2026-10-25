import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { AIGeneratePanel } from '@/components/ai/AIGeneratePanel';
import type { GenerationKind } from '@/types/ai';

/**
 * The AI entry point for surfaces that do not already have a create dialog to
 * fold it into.
 *
 * Landing pages put the panel inside their template gallery, because choosing
 * a template and describing a page are two answers to the same question. Forms,
 * email templates and campaigns have no gallery to join, so they get this.
 */
interface AIGenerateDialogProps {
  kind: GenerationKind;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerated: (resultId: string) => void;
  title: string;
  description: string;
}

export const AIGenerateDialog = ({
  kind,
  open,
  onOpenChange,
  onGenerated,
  title,
  description,
}: AIGenerateDialogProps) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="flex max-h-[90vh] max-w-2xl flex-col overflow-hidden">
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>{description}</DialogDescription>
      </DialogHeader>
      <AIGeneratePanel
        kind={kind}
        onGenerated={(id) => {
          onOpenChange(false);
          onGenerated(id);
        }}
        onCancel={() => onOpenChange(false)}
      />
    </DialogContent>
  </Dialog>
);
