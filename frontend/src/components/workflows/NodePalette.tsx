import { DragEvent } from 'react';
import {
  FileText,
  Tag,
  UserPlus,
  MailOpen,
  MousePointer,
  Calendar,
  Mail,
  UserCog,
  Clock,
  Webhook,
  Target,
  GitBranch,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { NODE_TYPES, WorkflowNodeType } from '@/types/workflow';

interface NodePaletteItemProps {
  type: WorkflowNodeType;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  category: 'trigger' | 'action' | 'condition';
}

const iconMap: Record<string, React.ReactNode> = {
  FileText: <FileText className="h-4 w-4" />,
  Tag: <Tag className="h-4 w-4" />,
  TagOff: <Tag className="h-4 w-4" />,
  TagPlus: <Tag className="h-4 w-4" />,
  TagMinus: <Tag className="h-4 w-4" />,
  UserPlus: <UserPlus className="h-4 w-4" />,
  MailOpen: <MailOpen className="h-4 w-4" />,
  MousePointerClick: <MousePointer className="h-4 w-4" />,
  Calendar: <Calendar className="h-4 w-4" />,
  Mail: <Mail className="h-4 w-4" />,
  UserCog: <UserCog className="h-4 w-4" />,
  Clock: <Clock className="h-4 w-4" />,
  Webhook: <Webhook className="h-4 w-4" />,
  Target: <Target className="h-4 w-4" />,
  GitBranch: <GitBranch className="h-4 w-4" />,
};

function NodePaletteItem({
  type,
  label,
  description,
  icon,
  color,
  category,
}: NodePaletteItemProps) {
  const onDragStart = (event: DragEvent<HTMLDivElement>) => {
    event.dataTransfer.setData('application/reactflow', type);
    event.dataTransfer.setData('nodeLabel', label);
    event.dataTransfer.effectAllowed = 'move';
  };

  const categoryStyles = {
    trigger: 'border-info/[.30] hover:border-info/[.50] hover:bg-info/[.10]',
    action: 'border-success/[.30] hover:border-success/[.50] hover:bg-success/[.10]',
    condition: 'border-warning/[.30] hover:border-warning/[.50] hover:bg-warning/[.10]',
  };

  return (
    <div
      draggable
      onDragStart={onDragStart}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border cursor-grab',
        'transition-all duration-150 active:cursor-grabbing',
        categoryStyles[category]
      )}
    >
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
        style={{ backgroundColor: color + '20', color }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{label}</p>
        <p className="text-xs text-muted-foreground truncate">{description}</p>
      </div>
    </div>
  );
}

export default function NodePalette() {
  const triggers = NODE_TYPES.filter((n) => n.category === 'trigger');
  const actions = NODE_TYPES.filter(
    (n) => n.category === 'action' && n.type !== 'action_goal'
  );
  const conditions = NODE_TYPES.filter((n) => n.category === 'condition');
  const goals = NODE_TYPES.filter((n) => n.type === 'action_goal');

  return (
    <div className="p-4 space-y-6">
      <div>
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Triggers
        </h3>
        <div className="space-y-2">
          {triggers.map((node) => (
            <NodePaletteItem
              key={node.type}
              type={node.type}
              label={node.label}
              description={node.description}
              icon={iconMap[node.icon] || <FileText className="h-4 w-4" />}
              color={node.color}
              category="trigger"
            />
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Actions
        </h3>
        <div className="space-y-2">
          {actions.map((node) => (
            <NodePaletteItem
              key={node.type}
              type={node.type}
              label={node.label}
              description={node.description}
              icon={iconMap[node.icon] || <Mail className="h-4 w-4" />}
              color={node.color}
              category="action"
            />
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Logic
        </h3>
        <div className="space-y-2">
          {conditions.map((node) => (
            <NodePaletteItem
              key={node.type}
              type={node.type}
              label={node.label}
              description={node.description}
              icon={iconMap[node.icon] || <GitBranch className="h-4 w-4" />}
              color={node.color}
              category="condition"
            />
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Goals
        </h3>
        <div className="space-y-2">
          {goals.map((node) => (
            <NodePaletteItem
              key={node.type}
              type={node.type}
              label={node.label}
              description={node.description}
              icon={iconMap[node.icon] || <Target className="h-4 w-4" />}
              color={node.color}
              category="action"
            />
          ))}
        </div>
      </div>

      <div className="pt-4 border-t">
        <p className="text-xs text-subtle-foreground text-center">
          Drag nodes to the canvas to build your workflow
        </p>
      </div>
    </div>
  );
}
