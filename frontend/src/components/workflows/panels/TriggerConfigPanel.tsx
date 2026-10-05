import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { TriggerNodeType } from '@/types/workflow';
import { useQuery } from '@tanstack/react-query';
import { formsApi } from '@/api/forms';
import apiClient from '@/api/client';
import { crmApi } from '@/api/crm';

interface TriggerConfigPanelProps {
  nodeType: TriggerNodeType;
  config: Record<string, unknown>;
  label: string;
  onChange: (config: Record<string, unknown>) => void;
  onLabelChange: (label: string) => void;
}

export default function TriggerConfigPanel({
  nodeType,
  config,
  label,
  onChange,
  onLabelChange,
}: TriggerConfigPanelProps) {
  // Fetch forms for form submission trigger
  const { data: formsData } = useQuery({
    queryKey: ['forms-list'],
    queryFn: () => formsApi.getForms({ page_size: 100 }),
    enabled: nodeType === 'trigger_form_submission',
  });

  // Fetch tags for tag triggers
  const { data: tagsData } = useQuery({
    queryKey: ['tags-list'],
    queryFn: async () => {
      const response = await apiClient.get('/tags');
      return response.data;
    },
    enabled:
      nodeType === 'trigger_tag_added' || nodeType === 'trigger_tag_removed',
  });

  // Fetch pipelines for deal triggers
  const { data: pipelines = [] } = useQuery({
    queryKey: ['pipelines'],
    queryFn: crmApi.getPipelines,
    enabled:
      nodeType === 'trigger_deal_stage_changed' ||
      nodeType === 'trigger_deal_created',
  });

  // Fetch stages for the selected pipeline (deal stage changed)
  const selectedPipelineId = config.pipeline_id as string | undefined;
  const { data: pipelineDetail } = useQuery({
    queryKey: ['pipeline', selectedPipelineId],
    queryFn: () => crmApi.getPipeline(selectedPipelineId!),
    enabled: nodeType === 'trigger_deal_stage_changed' && !!selectedPipelineId,
  });
  const stages = pipelineDetail?.stages || [];

  const forms = formsData?.data || [];
  const tags = tagsData?.results || tagsData || [];

  const renderFormSubmissionConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>Form</Label>
        <Select
          value={(config.form_id as string) || ''}
          onValueChange={(value) => {
            const form = forms.find((f: any) => f.id === value);
            onChange({
              ...config,
              form_id: value,
              form_name: form?.name || '',
            });
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a form" />
          </SelectTrigger>
          <SelectContent>
            {forms.map((form: any) => (
              <SelectItem key={form.id} value={form.id}>
                {form.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-500 mt-1">
          Workflow triggers when this form is submitted
        </p>
      </div>
    </div>
  );

  const renderTagConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>Tag</Label>
        <Select
          value={(config.tag_id as string) || ''}
          onValueChange={(value) => {
            const tag = tags.find((t: any) => t.id === value);
            onChange({
              ...config,
              tag_id: value,
              tag_name: tag?.name || '',
            });
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a tag" />
          </SelectTrigger>
          <SelectContent>
            {tags.map((tag: any) => (
              <SelectItem key={tag.id} value={tag.id}>
                {tag.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-500 mt-1">
          {nodeType === 'trigger_tag_added'
            ? 'Workflow triggers when this tag is added to a contact'
            : 'Workflow triggers when this tag is removed from a contact'}
        </p>
      </div>
    </div>
  );

  const renderDateFieldConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>Date Field Name</Label>
        <Input
          value={(config.field_name as string) || ''}
          onChange={(e) =>
            onChange({ ...config, field_name: e.target.value })
          }
          placeholder="e.g., birthday, anniversary"
        />
        <p className="text-xs text-gray-500 mt-1">
          The contact field containing the date
        </p>
      </div>

      <div>
        <Label>Days Offset</Label>
        <Input
          type="number"
          value={(config.offset_days as number) || 0}
          onChange={(e) =>
            onChange({ ...config, offset_days: parseInt(e.target.value) || 0 })
          }
        />
        <p className="text-xs text-gray-500 mt-1">
          Days before (negative) or after (positive) the date
        </p>
      </div>

      <div>
        <Label>Time (24h)</Label>
        <Input
          type="time"
          value={(config.time as string) || '09:00'}
          onChange={(e) => onChange({ ...config, time: e.target.value })}
        />
        <p className="text-xs text-gray-500 mt-1">
          Time of day to trigger the workflow
        </p>
      </div>
    </div>
  );

  const renderNoConfig = () => (
    <p className="text-sm text-gray-500">
      This trigger has no additional configuration. It will fire automatically
      when the event occurs.
    </p>
  );

  const renderDealStageChangedConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>Pipeline</Label>
        <Select
          value={(config.pipeline_id as string) || ''}
          onValueChange={(value) => {
            const pipeline = pipelines.find((p) => p.id === value);
            onChange({
              ...config,
              pipeline_id: value,
              pipeline_name: pipeline?.name || '',
              to_stage_id: '',
              from_stage_id: '',
            });
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a pipeline" />
          </SelectTrigger>
          <SelectContent>
            {pipelines.map((p) => (
              <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {stages.length > 0 && (
        <>
          <div>
            <Label>From Stage (optional)</Label>
            <Select
              value={(config.from_stage_id as string) || ''}
              onValueChange={(value) =>
                onChange({ ...config, from_stage_id: value || undefined })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Any stage" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Any stage</SelectItem>
                {stages.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>To Stage (optional)</Label>
            <Select
              value={(config.to_stage_id as string) || ''}
              onValueChange={(value) =>
                onChange({ ...config, to_stage_id: value || undefined })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Any stage" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Any stage</SelectItem>
                {stages.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      )}
      <p className="text-xs text-gray-500">
        Fires when a deal moves between stages. Leave stage filters empty to match any transition.
      </p>
    </div>
  );

  const renderDealCreatedConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>Pipeline (optional filter)</Label>
        <Select
          value={(config.pipeline_id as string) || ''}
          onValueChange={(value) => {
            const pipeline = pipelines.find((p) => p.id === value);
            onChange({ ...config, pipeline_id: value || undefined, pipeline_name: pipeline?.name || '' });
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Any pipeline" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Any pipeline</SelectItem>
            {pipelines.map((p) => (
              <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <p className="text-xs text-gray-500">
        Fires when a deal is created. The deal's primary contact must be set for the workflow to run.
      </p>
    </div>
  );

  const renderConfig = () => {
    switch (nodeType) {
      case 'trigger_form_submission':
        return renderFormSubmissionConfig();
      case 'trigger_tag_added':
      case 'trigger_tag_removed':
        return renderTagConfig();
      case 'trigger_date_field':
        return renderDateFieldConfig();
      case 'trigger_deal_stage_changed':
        return renderDealStageChangedConfig();
      case 'trigger_deal_created':
        return renderDealCreatedConfig();
      case 'trigger_contact_created':
      case 'trigger_email_opened':
      case 'trigger_email_clicked':
        return renderNoConfig();
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Label */}
      <div>
        <Label>Node Label</Label>
        <Input
          value={label || ''}
          onChange={(e) => onLabelChange(e.target.value)}
          placeholder="Enter a custom label"
        />
        <p className="text-xs text-gray-500 mt-1">
          Optional: Give this node a descriptive name
        </p>
      </div>

      {/* Type-specific config */}
      {renderConfig()}
    </div>
  );
}
