import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import { useLandingPageTemplates } from '@/hooks/useLandingPageTemplates';
import { FileText, Layout, Search } from 'lucide-react';
import type { TemplateCategory, LandingPageTemplate } from '@/types/landing-page';
import { templateCategoryLabels } from '@/types/landing-page';

interface TemplateSelectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (templateId: string | null, name: string) => void;
  isLoading?: boolean;
}

const categories: (TemplateCategory | 'all')[] = [
  'all',
  'lead_generation',
  'webinar',
  'ebook',
  'product_launch',
  'event',
  'coming_soon',
  'thank_you',
  'blank',
];

export const TemplateSelectionDialog = ({
  open,
  onOpenChange,
  onSelect,
  isLoading,
}: TemplateSelectionDialogProps) => {
  const [selectedCategory, setSelectedCategory] = useState<TemplateCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [pageName, setPageName] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<LandingPageTemplate | null>(null);

  const { templates, isLoading: templatesLoading } = useLandingPageTemplates(
    selectedCategory === 'all'
      ? { search: searchQuery || undefined }
      : { category: selectedCategory, search: searchQuery || undefined }
  );

  const handleSelect = () => {
    if (!pageName.trim()) return;
    onSelect(selectedTemplate?.id || null, pageName.trim());
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Create New Landing Page</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Page Name Input */}
          <div className="space-y-2">
            <Label htmlFor="pageName">Page Name *</Label>
            <Input
              id="pageName"
              placeholder="Enter page name..."
              value={pageName}
              onChange={(e) => setPageName(e.target.value)}
            />
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Category Tabs */}
          <Tabs
            value={selectedCategory}
            onValueChange={(v) => setSelectedCategory(v as TemplateCategory | 'all')}
          >
            <TabsList className="w-full flex-wrap h-auto gap-1 p-1">
              {categories.map((cat) => (
                <TabsTrigger key={cat} value={cat} className="text-xs">
                  {cat === 'all' ? 'All' : templateCategoryLabels[cat]}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value={selectedCategory} className="mt-4">
              <div className="grid grid-cols-3 gap-4 max-h-[400px] overflow-y-auto p-1">
                {/* Start Blank Option */}
                <Card
                  className={`cursor-pointer transition-all hover:shadow-md ${
                    selectedTemplate === null
                      ? 'ring-2 ring-primary'
                      : 'hover:border-primary/50'
                  }`}
                  onClick={() => setSelectedTemplate(null)}
                >
                  <div className="aspect-video bg-muted flex items-center justify-center">
                    <Layout className="h-12 w-12 text-muted-foreground" />
                  </div>
                  <div className="p-3">
                    <h4 className="font-medium text-sm">Start Blank</h4>
                    <p className="text-xs text-muted-foreground">
                      Start with a clean canvas
                    </p>
                  </div>
                </Card>

                {/* Templates */}
                {templatesLoading ? (
                  <div className="col-span-2 flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                  </div>
                ) : (
                  templates.map((template) => (
                    <Card
                      key={template.id}
                      className={`cursor-pointer transition-all hover:shadow-md ${
                        selectedTemplate?.id === template.id
                          ? 'ring-2 ring-primary'
                          : 'hover:border-primary/50'
                      }`}
                      onClick={() => setSelectedTemplate(template)}
                    >
                      <div className="aspect-video bg-muted overflow-hidden">
                        {template.thumbnail ? (
                          <img
                            src={template.thumbnail}
                            alt={template.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <FileText className="h-12 w-12 text-muted-foreground" />
                          </div>
                        )}
                      </div>
                      <div className="p-3">
                        <h4 className="font-medium text-sm truncate">{template.name}</h4>
                        <p className="text-xs text-muted-foreground">
                          {template.category_display}
                        </p>
                      </div>
                    </Card>
                  ))
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 pt-4 border-t mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSelect}
            disabled={!pageName.trim() || isLoading}
          >
            {isLoading ? 'Creating...' : selectedTemplate ? 'Use Template' : 'Create Blank Page'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
