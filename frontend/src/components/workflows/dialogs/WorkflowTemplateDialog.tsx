import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { FileText, Plus, Loader2 } from 'lucide-react';
import { useWorkflowTemplates, useWorkflowTemplateMutations } from '@/hooks/useWorkflowTemplates';
import { TemplateCategory } from '@/types/workflow';

interface WorkflowTemplateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const categoryLabels: Record<TemplateCategory, string> = {
  welcome_series: 'Welcome Series',
  lead_nurturing: 'Lead Nurturing',
  re_engagement: 'Re-engagement',
  onboarding: 'Onboarding',
  promotional: 'Promotional',
  custom: 'Custom',
};

export default function WorkflowTemplateDialog({
  open,
  onOpenChange,
}: WorkflowTemplateDialogProps) {
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  const { data: templatesData, isLoading } = useWorkflowTemplates({
    category: selectedCategory !== 'all' ? (selectedCategory as TemplateCategory) : undefined,
  });

  const { useTemplate } = useWorkflowTemplateMutations();

  const templates = templatesData?.data || [];

  const handleUseTemplate = async () => {
    if (!selectedTemplate) return;

    try {
      const workflow = await useTemplate.mutateAsync(selectedTemplate);
      onOpenChange(false);
      navigate(`/workflows/${workflow.id}/edit`);
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleStartBlank = () => {
    onOpenChange(false);
    navigate('/workflows/new');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Create New Workflow</DialogTitle>
          <DialogDescription>
            Start from a template or create a blank workflow
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-4 py-4">
          <Button
            variant="outline"
            className="flex-1 h-20 flex-col"
            onClick={handleStartBlank}
          >
            <Plus className="h-6 w-6 mb-2" />
            Start from Scratch
          </Button>
        </div>

        <div className="border-t pt-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Or choose a template</h3>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {Object.entries(categoryLabels).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="overflow-y-auto max-h-[300px] space-y-2 pr-2">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
              </div>
            ) : templates.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No templates available
              </div>
            ) : (
              templates.map((template) => (
                <div
                  key={template.id}
                  onClick={() => setSelectedTemplate(template.id)}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedTemplate === template.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="h-10 w-10 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
                    <FileText className="h-5 w-5 text-gray-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-sm">{template.name}</p>
                      {template.is_system && (
                        <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                          System
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                      {template.description}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {categoryLabels[template.category]}
                      {template.usage_count > 0 && (
                        <> &middot; Used {template.usage_count} times</>
                      )}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="border-t pt-4 flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleUseTemplate}
            disabled={!selectedTemplate || useTemplate.isPending}
          >
            {useTemplate.isPending && (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            )}
            Use Template
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
