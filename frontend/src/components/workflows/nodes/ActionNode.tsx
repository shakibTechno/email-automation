import { memo } from 'react';
import { NodeProps } from 'reactflow';
import BaseNode, { BaseNodeData } from './BaseNode';
import {
  Mail,
  Tag,
  UserCog,
  Clock,
  Webhook,
  Target,
  Briefcase,
} from 'lucide-react';
import { ActionNodeType } from '@/types/workflow';

interface ActionNodeData extends BaseNodeData {
  node_type: ActionNodeType;
}

const icons: Record<ActionNodeType, React.ReactNode> = {
  action_send_email: <Mail className="h-4 w-4" />,
  action_add_tag: <Tag className="h-4 w-4" />,
  action_remove_tag: <Tag className="h-4 w-4" />,
  action_update_contact: <UserCog className="h-4 w-4" />,
  action_wait: <Clock className="h-4 w-4" />,
  action_webhook: <Webhook className="h-4 w-4" />,
  action_goal: <Target className="h-4 w-4" />,
  action_update_deal: <Briefcase className="h-4 w-4" />,
};

function ActionNode(props: NodeProps<ActionNodeData>) {
  const { data } = props;
  const icon = icons[data.node_type] || <Mail className="h-4 w-4" />;
  const isGoal = data.node_type === 'action_goal';

  const getConfigPreview = () => {
    const config = data.config as Record<string, unknown>;

    switch (data.node_type) {
      case 'action_send_email':
        return config.template_name ? (
          <span>Template: {config.template_name as string}</span>
        ) : null;
      case 'action_add_tag':
      case 'action_remove_tag':
        return config.tag_name ? (
          <span>Tag: {config.tag_name as string}</span>
        ) : null;
      case 'action_update_contact':
        return config.field ? (
          <span>
            {config.operation as string} {config.field as string}
          </span>
        ) : null;
      case 'action_wait':
        return config.duration ? (
          <span>
            {config.duration as number} {config.unit as string}
          </span>
        ) : null;
      case 'action_webhook':
        return config.url ? (
          <span className="truncate max-w-[150px] block">
            {config.method as string || 'POST'}: {config.url as string}
          </span>
        ) : null;
      case 'action_goal':
        return <span className="text-purple-600">Mark goal reached</span>;
      case 'action_update_deal':
        return config.field ? (
          <span>
            Set {config.field as string}: {config.value as string}
          </span>
        ) : null;
      default:
        return null;
    }
  };

  const isConfigured = () => {
    const config = data.config as Record<string, unknown>;
    switch (data.node_type) {
      case 'action_send_email':
        return !!config.template_id;
      case 'action_add_tag':
      case 'action_remove_tag':
        return !!config.tag_id;
      case 'action_update_contact':
        return !!config.field && !!config.operation;
      case 'action_wait':
        return !!config.duration;
      case 'action_webhook':
        return !!config.url;
      case 'action_goal':
        return true;
      case 'action_update_deal':
        return !!config.field && !!config.value;
      default:
        return false;
    }
  };

  return (
    <BaseNode
      {...props}
      data={{ ...data, isConfigured: isConfigured() }}
      icon={icon}
      color={isGoal ? '#8b5cf6' : '#22c55e'}
      category={isGoal ? 'goal' : 'action'}
      hasSourceHandle={!isGoal}
    >
      {getConfigPreview()}
    </BaseNode>
  );
}

export default memo(ActionNode);
