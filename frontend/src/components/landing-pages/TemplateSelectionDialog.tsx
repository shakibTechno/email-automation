import { useEffect, useMemo, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { TemplatePreview } from '@/components/landing-pages/TemplatePreview';
import { AIGeneratePanel } from '@/components/ai/AIGeneratePanel';
import { useLandingPageTemplates } from '@/hooks/useLandingPageTemplates';
import { useAIConfig } from '@/hooks/useAI';
import { cn } from '@/lib/utils';
import { Check, Eye, Layout, Loader2, Search, Sparkles } from 'lucide-react';
import type { TemplateCategory, LandingPageTemplate } from '@/types/landing-page';
import { templateCategoryLabels } from '@/types/landing-page';

interface TemplateSelectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (templateId: string | null, name: string) => void;
  /** Called when AI generation produced a page, which already exists by then. */
  onGenerated?: (landingPageId: string) => void;
  isLoading?: boolean;
}

const BLANK_NAME = 'Untitled page';

type Mode = 'template' | 'ai';

export const TemplateSelectionDialog = ({
  open,
  onOpenChange,
  onSelect,
  onGenerated,
  isLoading,
}: TemplateSelectionDialogProps) => {
  const [mode, setMode] = useState<Mode>('template');
  const { config: aiConfig } = useAIConfig();
  const [selectedCategory, setSelectedCategory] = useState<TemplateCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [pageName, setPageName] = useState('');
  const [nameTouched, setNameTouched] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<LandingPageTemplate | null>(null);
  const [previewing, setPreviewing] = useState<LandingPageTemplate | null>(null);

  // The category list is fetched unfiltered so the tabs can be built from what
  // actually exists. The old dialog hard-coded all eight categories, so seven
  // of them were dead tabs leading to an empty grid.
  const { templates: allTemplates } = useLandingPageTemplates();
  const { templates, isLoading: templatesLoading } = useLandingPageTemplates(
    selectedCategory === 'all'
      ? { search: searchQuery || undefined }
      : { category: selectedCategory, search: searchQuery || undefined }
  );

  const categories = useMemo(() => {
    const present = new Set(allTemplates.map((t) => t.category));
    return (['all', ...Object.keys(templateCategoryLabels)] as const).filter(
      (c) => c === 'all' || present.has(c as TemplateCategory)
    ) as (TemplateCategory | 'all')[];
  }, [allTemplates]);

  useEffect(() => {
    if (!open) return;
    setSelectedTemplate(null);
    setSelectedCategory('all');
    setSearchQuery('');
    setPageName('');
    setNameTouched(false);
    setMode('template');
  }, [open]);

  // Choosing is the decision; the name is a confirmation of it. Pre-filling
  // from the template means the field is answered before it is asked, which is
  // what lets the gallery come first.
  const choose = (template: LandingPageTemplate | null) => {
    setSelectedTemplate(template);
    if (!nameTouched) setPageName(template ? template.name : BLANK_NAME);
  };

  const name = pageName.trim();

  const handleCreate = () => {
    if (!name) return;
    onSelect(selectedTemplate?.id || null, name);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="flex max-h-[90vh] max-w-5xl flex-col overflow-hidden">
          <DialogHeader>
            <DialogTitle>New landing page</DialogTitle>
            <DialogDescription>
              Start from a template, build from an empty canvas, or describe the page you want.
            </DialogDescription>
          </DialogHeader>

          {/* The AI entry point is always visible, even unconfigured — the
              panel itself explains what to connect. Hiding it would mean
              nobody discovers the feature exists. */}
          <div className="flex gap-1 rounded-lg bg-secondary p-0.5">
            <button
              type="button"
              onClick={() => setMode('template')}
              className={cn(
                'flex-1 rounded-md px-3 py-1.5 text-[12.5px] font-medium transition-colors',
                mode === 'template'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              Templates
            </button>
            <button
              type="button"
              onClick={() => setMode('ai')}
              className={cn(
                'flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-[12.5px] font-medium transition-colors',
                mode === 'ai'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Sparkles className="h-3.5 w-3.5" />
              Generate with AI
              {!aiConfig?.is_ready && (
                <span className="text-[10px] text-subtle-foreground">· setup</span>
              )}
            </button>
          </div>

          {mode === 'ai' ? (
            <AIGeneratePanel
              kind="landing_page"
              onGenerated={(id) => {
                onOpenChange(false);
                onGenerated?.(id);
              }}
              onCancel={() => onOpenChange(false)}
            />
          ) : (
          <>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[200px] flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search templates…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-9 pl-9"
              />
            </div>
            {categories.length > 1 && (
              <div className="flex flex-wrap gap-1">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={cn(
                      'rounded-md px-2.5 py-1.5 text-[12px] font-medium transition-colors',
                      selectedCategory === cat
                        ? 'bg-secondary text-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    )}
                  >
                    {cat === 'all' ? 'All' : templateCategoryLabels[cat]}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* `auto-rows-max` and `content-start`: the grid is a flex child with
              a definite height, so without them CSS Grid divides that height
              between the rows and squashes every card instead of letting the
              list scroll. */}
          <div className="-mx-1 grid flex-1 auto-rows-max grid-cols-2 content-start gap-3 overflow-y-auto p-1 md:grid-cols-3">
            {/* Blank */}
            <button
              type="button"
              onClick={() => choose(null)}
              className={cn(
                'overflow-hidden rounded-lg border bg-card text-left transition-colors hover:border-brand/50',
                selectedTemplate === null && 'border-brand ring-1 ring-brand'
              )}
            >
              <div className="flex h-[150px] items-center justify-center border-b bg-secondary/40">
                <Layout className="h-7 w-7 text-subtle-foreground" />
              </div>
              <div className="flex items-center gap-1.5 p-2.5">
                <span className="truncate text-[13px] font-medium">Blank page</span>
                {selectedTemplate === null && (
                  <Check className="ml-auto h-3.5 w-3.5 flex-none text-brand" />
                )}
              </div>
            </button>

            {templatesLoading
              ? [0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="flex h-[196px] items-center justify-center rounded-lg border bg-card"
                  >
                    <Loader2 className="h-5 w-5 animate-spin text-subtle-foreground" />
                  </div>
                ))
              : templates.map((template) => {
                  const active = selectedTemplate?.id === template.id;
                  return (
                    <div
                      key={template.id}
                      className={cn(
                        'group relative overflow-hidden rounded-lg border bg-card transition-colors hover:border-brand/50',
                        active && 'border-brand ring-1 ring-brand'
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => choose(template)}
                        className="block w-full text-left"
                      >
                        <div className="border-b">
                          <TemplatePreview templateId={template.id} />
                        </div>
                        <div className="flex items-center gap-1.5 p-2.5">
                          <span className="truncate text-[13px] font-medium">
                            {template.name}
                          </span>
                          <span className="ml-auto flex-none text-[11px] text-subtle-foreground">
                            {active ? (
                              <Check className="h-3.5 w-3.5 text-brand" />
                            ) : (
                              template.category_display
                            )}
                          </span>
                        </div>
                      </button>

                      {/* Judging a template from a 150px card only goes so far;
                          this opens it at full size before committing. */}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="absolute right-2 top-2 h-7 opacity-0 transition-opacity focus-visible:opacity-100 group-hover:opacity-100"
                        onClick={() => setPreviewing(template)}
                      >
                        <Eye className="h-3.5 w-3.5" /> Preview
                      </Button>
                    </div>
                  );
                })}
          </div>

          <div className="flex flex-wrap items-end gap-3 border-t pt-4">
            <div className="min-w-[220px] flex-1 space-y-1.5">
              <Label htmlFor="pageName">Page name</Label>
              <Input
                id="pageName"
                placeholder={BLANK_NAME}
                value={pageName}
                onChange={(e) => {
                  setPageName(e.target.value);
                  setNameTouched(true);
                }}
              />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={!name || isLoading}>
                {isLoading ? 'Creating…' : 'Create page'}
              </Button>
            </div>
          </div>
          </>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!previewing} onOpenChange={(o) => !o && setPreviewing(null)}>
        <DialogContent className="max-w-5xl">
          <DialogHeader>
            <DialogTitle>{previewing?.name}</DialogTitle>
            <DialogDescription>
              {previewing?.category_display}
              {previewing?.description ? ` — ${previewing.description}` : ''}
            </DialogDescription>
          </DialogHeader>
          {previewing && (
            <div className="overflow-hidden rounded-lg border">
              <TemplatePreview templateId={previewing.id} height={460} />
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setPreviewing(null)}>
              Close
            </Button>
            <Button
              onClick={() => {
                choose(previewing);
                setPreviewing(null);
              }}
            >
              Use this template
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};
