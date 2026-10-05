import { Button } from '@/components/ui/button';
import {
  Save,
  Play,
  Pause,
  CheckCircle,
  ArrowLeft,
  Loader2,
} from 'lucide-react';
import { WorkflowStatus } from '@/types/workflow';

interface WorkflowToolbarProps {
  workflowName: string;
  status: WorkflowStatus;
  isSaving?: boolean;
  isActivating?: boolean;
  hasChanges?: boolean;
  onSave: () => void;
  onValidate: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
  onBack: () => void;
}

export default function WorkflowToolbar({
  workflowName,
  status,
  isSaving = false,
  isActivating = false,
  hasChanges = false,
  onSave,
  onValidate,
  onActivate,
  onDeactivate,
  onBack,
}: WorkflowToolbarProps) {
  const isActive = status === 'active';

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b bg-white">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-lg font-semibold">{workflowName || 'Untitled Workflow'}</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                status === 'active'
                  ? 'bg-success/[.14] text-success'
                  : status === 'paused'
                  ? 'bg-warning/[.14] text-warning'
                  : 'bg-secondary text-muted-foreground'
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
            {hasChanges && (
              <span className="text-warning">• Unsaved changes</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          onClick={onValidate}
          disabled={isSaving || isActivating}
        >
          <CheckCircle className="h-4 w-4 mr-2" />
          Validate
        </Button>

        <Button
          variant="outline"
          onClick={onSave}
          disabled={isSaving || isActivating || !hasChanges}
        >
          {isSaving ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save
        </Button>

        {isActive ? (
          <Button
            variant="destructive"
            onClick={onDeactivate}
            disabled={isSaving || isActivating}
          >
            {isActivating ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Pause className="h-4 w-4 mr-2" />
            )}
            Pause
          </Button>
        ) : (
          <Button
            onClick={onActivate}
            disabled={isSaving || isActivating || hasChanges}
          >
            {isActivating ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Activate
          </Button>
        )}
      </div>
    </div>
  );
}
