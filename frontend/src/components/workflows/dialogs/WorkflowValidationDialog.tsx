import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { WorkflowValidation } from '@/types/workflow';

interface WorkflowValidationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  validation: WorkflowValidation | null;
  isLoading?: boolean;
}

export default function WorkflowValidationDialog({
  open,
  onOpenChange,
  validation,
  isLoading,
}: WorkflowValidationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Workflow Validation</DialogTitle>
          <DialogDescription>
            Check if your workflow is correctly configured
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-info" />
            </div>
          ) : validation ? (
            <div className="space-y-4">
              {/* Status */}
              <div
                className={`flex items-center gap-3 p-4 rounded-lg ${
                  validation.is_valid
                    ? 'bg-success/[.10] text-success'
                    : 'bg-destructive/[.10] text-destructive'
                }`}
              >
                {validation.is_valid ? (
                  <CheckCircle className="h-6 w-6 text-success" />
                ) : (
                  <XCircle className="h-6 w-6 text-destructive" />
                )}
                <div>
                  <p className="font-medium">
                    {validation.is_valid
                      ? 'Workflow is valid!'
                      : 'Validation failed'}
                  </p>
                  <p className="text-sm opacity-75">
                    {validation.is_valid
                      ? 'Your workflow is ready to be activated.'
                      : `${validation.errors.length} issue${
                          validation.errors.length !== 1 ? 's' : ''
                        } found`}
                  </p>
                </div>
              </div>

              {/* Errors */}
              {validation.errors.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-foreground">Issues:</p>
                  <ul className="space-y-2">
                    {validation.errors.map((error, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 text-sm text-destructive"
                      >
                        <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                        {error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">
              No validation data available
            </p>
          )}
        </div>

        <div className="flex justify-end">
          <Button onClick={() => onOpenChange(false)}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
