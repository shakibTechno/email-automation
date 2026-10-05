import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ActionNodeType } from '@/types/workflow';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { crmApi } from '@/api/crm';

interface ActionConfigPanelProps {
  nodeType: ActionNodeType;
  config: Record<string, unknown>;
  label: string;
  onChange: (config: Record<string, unknown>) => void;
  onLabelChange: (label: string) => void;
}

export default function ActionConfigPanel({
  nodeType,
  config,
  label,
  onChange,
  onLabelChange,
}: ActionConfigPanelProps) {
  // Fetch email templates
  const { data: templatesData } = useQuery({
    queryKey: ['templates-list'],
    queryFn: async () => {
      const response = await apiClient.get('/templates');
      return response.data;
    },
    enabled: nodeType === 'action_send_email',
  });

  // Fetch tags
  const { data: tagsData } = useQuery({
    queryKey: ['tags-list'],
    queryFn: async () => {
      const response = await apiClient.get('/tags');
      return response.data;
    },
    enabled:
      nodeType === 'action_add_tag' || nodeType === 'action_remove_tag',
  });

  const templates = templatesData?.results || templatesData || [];
  const tags = tagsData?.results || tagsData || [];

  // Fetch pipelines for update_deal action
  const { data: pipelines = [] } = useQuery({
    queryKey: ['pipelines'],
    queryFn: crmApi.getPipelines,
    enabled: nodeType === 'action_update_deal',
  });

  // Fetch stages when a pipeline is selected for update_deal
  const dealField = config.field as string | undefined;
  const selectedPipelineId = config.pipeline_id as string | undefined;
  const { data: pipelineDetail } = useQuery({
    queryKey: ['pipeline', selectedPipelineId],
    queryFn: () => crmApi.getPipeline(selectedPipelineId!),
    enabled: nodeType === 'action_update_deal' && dealField === 'stage' && !!selectedPipelineId,
  });
  const stages = pipelineDetail?.stages || [];

  const renderSendEmailConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>Email Template</Label>
        <Select
          value={(config.template_id as string) || ''}
          onValueChange={(value) => {
            const template = templates.find((t: any) => t.id === value);
            onChange({
              ...config,
              template_id: value,
              template_name: template?.name || '',
            });
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a template" />
          </SelectTrigger>
          <SelectContent>
            {templates.map((template: any) => (
              <SelectItem key={template.id} value={template.id}>
                {template.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label>Subject Override (optional)</Label>
        <Input
          value={(config.subject as string) || ''}
          onChange={(e) => onChange({ ...config, subject: e.target.value })}
          placeholder="Override template subject"
        />
        <p className="text-xs text-gray-500 mt-1">
          Leave blank to use the template's subject
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
          {nodeType === 'action_add_tag'
            ? 'This tag will be added to the contact'
            : 'This tag will be removed from the contact'}
        </p>
      </div>
    </div>
  );

  const renderUpdateContactConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>Field</Label>
        <Select
          value={(config.field as string) || ''}
          onValueChange={(value) => onChange({ ...config, field: value })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a field" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="lead_score">Lead Score</SelectItem>
            <SelectItem value="engagement_level">Engagement Level</SelectItem>
            <SelectItem value="first_name">First Name</SelectItem>
            <SelectItem value="last_name">Last Name</SelectItem>
            <SelectItem value="company">Company</SelectItem>
            <SelectItem value="job_title">Job Title</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label>Operation</Label>
        <Select
          value={(config.operation as string) || 'set'}
          onValueChange={(value) => onChange({ ...config, operation: value })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select operation" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="set">Set to value</SelectItem>
            <SelectItem value="increment">Increment by</SelectItem>
            <SelectItem value="decrement">Decrement by</SelectItem>
            <SelectItem value="append">Append text</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label>Value</Label>
        <Input
          value={(config.value as string) || ''}
          onChange={(e) => onChange({ ...config, value: e.target.value })}
          placeholder="Enter value"
        />
      </div>
    </div>
  );

  const renderWaitConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>Duration</Label>
        <Input
          type="number"
          min={1}
          value={(config.duration as number) || 1}
          onChange={(e) =>
            onChange({ ...config, duration: parseInt(e.target.value) || 1 })
          }
        />
      </div>

      <div>
        <Label>Unit</Label>
        <Select
          value={(config.unit as string) || 'hours'}
          onValueChange={(value) => onChange({ ...config, unit: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="minutes">Minutes</SelectItem>
            <SelectItem value="hours">Hours</SelectItem>
            <SelectItem value="days">Days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <p className="text-sm text-gray-500">
        The workflow will pause for{' '}
        {(config.duration as number) || 1} {(config.unit as string) || 'hours'}{' '}
        before continuing
      </p>
    </div>
  );

  const renderWebhookConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>URL</Label>
        <Input
          type="url"
          value={(config.url as string) || ''}
          onChange={(e) => onChange({ ...config, url: e.target.value })}
          placeholder="https://example.com/webhook"
        />
      </div>

      <div>
        <Label>Method</Label>
        <Select
          value={(config.method as string) || 'POST'}
          onValueChange={(value) => onChange({ ...config, method: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="GET">GET</SelectItem>
            <SelectItem value="POST">POST</SelectItem>
            <SelectItem value="PUT">PUT</SelectItem>
            <SelectItem value="PATCH">PATCH</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label>Headers (JSON)</Label>
        <Textarea
          value={JSON.stringify(config.headers || {}, null, 2)}
          onChange={(e) => {
            try {
              const headers = JSON.parse(e.target.value);
              onChange({ ...config, headers });
            } catch {
              // Invalid JSON, don't update
            }
          }}
          placeholder='{"Authorization": "Bearer token"}'
          className="font-mono text-sm"
          rows={3}
        />
      </div>

      <p className="text-xs text-gray-500">
        Contact data will be automatically included in the request payload
      </p>
    </div>
  );

  const renderGoalConfig = () => (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        When the workflow reaches this node, it will mark the goal as reached
        for the contact. This is useful for tracking conversion goals.
      </p>
      <div className="bg-purple-50 p-3 rounded-lg">
        <p className="text-sm text-purple-700">
          Goal nodes do not have additional configuration. They simply mark the
          workflow goal as achieved.
        </p>
      </div>
    </div>
  );

  const renderUpdateDealConfig = () => (
    <div className="space-y-4">
      <div>
        <Label>Field to Update</Label>
        <Select
          value={(config.field as string) || ''}
          onValueChange={(value) =>
            onChange({ ...config, field: value, value: '', pipeline_id: '' })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a field" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="stage">Stage</SelectItem>
            <SelectItem value="priority">Priority</SelectItem>
            <SelectItem value="assigned_to">Assigned To (user ID)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {dealField === 'stage' && (
        <>
          <div>
            <Label>Pipeline</Label>
            <Select
              value={(config.pipeline_id as string) || ''}
              onValueChange={(value) => onChange({ ...config, pipeline_id: value, value: '' })}
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
            <div>
              <Label>Target Stage</Label>
              <Select
                value={(config.value as string) || ''}
                onValueChange={(value) => onChange({ ...config, value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a stage" />
                </SelectTrigger>
                <SelectContent>
                  {stages.map((s) => (
                    <SelectItem key={s.id} value={s.name}>{s.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </>
      )}

      {dealField === 'priority' && (
        <div>
          <Label>Priority</Label>
          <Select
            value={(config.value as string) || ''}
            onValueChange={(value) => onChange({ ...config, value })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="high">High</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {dealField === 'assigned_to' && (
        <div>
          <Label>User ID</Label>
          <Input
            value={(config.value as string) || ''}
            onChange={(e) => onChange({ ...config, value: e.target.value })}
            placeholder="Enter user UUID"
          />
          <p className="text-xs text-gray-500 mt-1">
            The UUID of the team member to assign the deal to
          </p>
        </div>
      )}

      <p className="text-xs text-gray-500">
        Updates the deal that triggered this workflow. Only available when triggered by a deal trigger.
      </p>
    </div>
  );

  const renderConfig = () => {
    switch (nodeType) {
      case 'action_send_email':
        return renderSendEmailConfig();
      case 'action_add_tag':
      case 'action_remove_tag':
        return renderTagConfig();
      case 'action_update_contact':
        return renderUpdateContactConfig();
      case 'action_wait':
        return renderWaitConfig();
      case 'action_webhook':
        return renderWebhookConfig();
      case 'action_goal':
        return renderGoalConfig();
      case 'action_update_deal':
        return renderUpdateDealConfig();
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
