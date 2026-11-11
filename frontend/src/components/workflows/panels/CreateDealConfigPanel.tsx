import { useQuery } from '@tanstack/react-query';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { crmApi } from '@/api/crm';

/**
 * Create Deal: open a deal for the contact.
 *
 * Hand-written rather than rendered from the catalogue because the stage list
 * depends on the pipeline chosen beside it, which a generic field renderer
 * cannot express — the same reason Update Deal has its own panel.
 */

interface Props {
  config: {
    pipeline_id?: string;
    stage_id?: string;
    title?: string;
    value?: string | number;
  };
  label: string;
  onChange: (config: Record<string, unknown>) => void;
  onLabelChange: (label: string) => void;
}

const FIRST_STAGE = '__first__';

export default function CreateDealConfigPanel({
  config, label, onChange, onLabelChange,
}: Props) {
  const { data: pipelines = [] } = useQuery({
    queryKey: ['pipelines'],
    queryFn: crmApi.getPipelines,
  });

  const pipelineId = config.pipeline_id || '';
  const { data: pipelineDetail } = useQuery({
    queryKey: ['pipeline', pipelineId],
    queryFn: () => crmApi.getPipeline(pipelineId),
    enabled: Boolean(pipelineId),
  });
  const stages = pipelineDetail?.stages || [];

  const set = (partial: Record<string, unknown>) =>
    onChange({ ...config, ...partial });

  return (
    <div className="space-y-5">
      <div>
        <Label>Step label</Label>
        <Input
          className="mt-1"
          value={label || ''}
          onChange={(event) => onLabelChange(event.target.value)}
          placeholder="Open a deal"
        />
      </div>

      <div>
        <Label>
          Pipeline<span className="ml-0.5 text-destructive">*</span>
        </Label>
        <Select
          value={pipelineId || undefined}
          onValueChange={(value) =>
            // Changing pipeline invalidates the stage: a stage id from the
            // old one would be rejected when a contact reached the step.
            set({ pipeline_id: value, stage_id: '' })
          }
        >
          <SelectTrigger className="mt-1">
            <SelectValue placeholder="Choose a pipeline" />
          </SelectTrigger>
          <SelectContent>
            {(pipelines as any[]).map((pipeline) => (
              <SelectItem key={pipeline.id} value={pipeline.id}>
                {pipeline.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {(pipelines as any[]).length === 0 && (
          <p className="mt-1 text-xs text-warning">
            No pipelines yet — create one first, or this step will fail when a
            contact reaches it.
          </p>
        )}
      </div>

      {pipelineId && (
        <div>
          <Label>Stage</Label>
          <Select
            value={config.stage_id || FIRST_STAGE}
            onValueChange={(value) =>
              set({ stage_id: value === FIRST_STAGE ? '' : value })
            }
          >
            <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={FIRST_STAGE}>The first stage</SelectItem>
              {(stages as any[]).map((stage) => (
                <SelectItem key={stage.id} value={stage.id}>
                  {stage.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <div>
        <Label>Deal title</Label>
        <Input
          className="mt-1"
          value={config.title || ''}
          placeholder="{{first_name}} {{last_name}}"
          onChange={(event) => set({ title: event.target.value })}
        />
        <p className="mt-1 text-xs text-muted-foreground">
          Merge tags work here. Leave it empty to name the deal after the
          contact.
        </p>
      </div>

      <div>
        <Label>Value</Label>
        <Input
          className="mt-1"
          type="number"
          min={0}
          value={config.value ?? ''}
          onChange={(event) => set({ value: event.target.value })}
        />
      </div>
    </div>
  );
}
