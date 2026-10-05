import { memo } from 'react';
import { NodeProps } from 'reactflow';
import BaseNode, { BaseNodeData } from './BaseNode';
import {
  FileText,
  Tag,
  UserPlus,
  MailOpen,
  MousePointer,
  Calendar,
  Briefcase,
  PlusSquare,
} from 'lucide-react';
import { TriggerNodeType } from '@/types/workflow';

interface TriggerNodeData extends BaseNodeData {
  node_type: TriggerNodeType;
}

const icons: Record<TriggerNodeType, React.ReactNode> = {
  trigger_form_submission: <FileText className="h-4 w-4" />,
  trigger_tag_added: <Tag className="h-4 w-4" />,
  trigger_tag_removed: <Tag className="h-4 w-4" />,
  trigger_contact_created: <UserPlus className="h-4 w-4" />,
  trigger_email_opened: <MailOpen className="h-4 w-4" />,
  trigger_email_clicked: <MousePointer className="h-4 w-4" />,
  trigger_date_field: <Calendar className="h-4 w-4" />,
  trigger_deal_stage_changed: <Briefcase className="h-4 w-4" />,
  trigger_deal_created: <PlusSquare className="h-4 w-4" />,
};

function TriggerNode(props: NodeProps<TriggerNodeData>) {
  const { data } = props;
  const icon = icons[data.node_type] || <FileText className="h-4 w-4" />;

  const getConfigPreview = () => {
    const config = data.config as Record<string, unknown>;

    switch (data.node_type) {
      case 'trigger_form_submission':
        return config.form_name ? (
          <span>Form: {config.form_name as string}</span>
        ) : null;
      case 'trigger_tag_added':
      case 'trigger_tag_removed':
        return config.tag_name ? (
          <span>Tag: {config.tag_name as string}</span>
        ) : null;
      case 'trigger_date_field':
        return config.field_name ? (
          <span>
            Field: {config.field_name as string}
            {config.offset_days !== undefined && (
              <>, {config.offset_days as number} days</>
            )}
          </span>
        ) : null;
      case 'trigger_deal_stage_changed':
        return config.pipeline_name ? (
          <span>
            {config.pipeline_name as string}
            {!!config.to_stage_id && <> → {config.to_stage_id as string}</>}
          </span>
        ) : null;
      case 'trigger_deal_created':
        return config.pipeline_name ? (
          <span>Pipeline: {config.pipeline_name as string}</span>
        ) : <span>Any pipeline</span>;
      default:
        return null;
    }
  };

  const isConfigured = () => {
    const config = data.config as Record<string, unknown>;
    switch (data.node_type) {
      case 'trigger_form_submission':
        return !!config.form_id;
      case 'trigger_tag_added':
      case 'trigger_tag_removed':
        return !!config.tag_id;
      case 'trigger_date_field':
        return !!config.field_name;
      case 'trigger_contact_created':
      case 'trigger_email_opened':
      case 'trigger_email_clicked':
        return true;
      case 'trigger_deal_stage_changed':
        return !!config.pipeline_id;
      case 'trigger_deal_created':
        return true;
      default:
        return false;
    }
  };

  return (
    <BaseNode
      {...props}
      data={{ ...data, isConfigured: isConfigured() }}
      icon={icon}
      color="#3b82f6"
      category="trigger"
      hasTargetHandle={false}
    >
      {getConfigPreview()}
    </BaseNode>
  );
}

export default memo(TriggerNode);
