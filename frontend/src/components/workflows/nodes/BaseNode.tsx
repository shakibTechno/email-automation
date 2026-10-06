import { memo, ReactNode } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { cn } from '@/lib/utils';

export interface BaseNodeData {
  label: string;
  node_type: string;
  config: Record<string, unknown>;
  isConfigured?: boolean;
}

interface BaseNodeProps extends NodeProps<BaseNodeData> {
  icon: ReactNode;
  color: string;
  category: 'trigger' | 'action' | 'condition' | 'goal';
  children?: ReactNode;
  hasSourceHandle?: boolean;
  hasTargetHandle?: boolean;
  sourceHandles?: { id: string; position: Position; label?: string }[];
}

function BaseNode({
  data,
  selected,
  icon,
  color,
  category,
  children,
  hasSourceHandle = true,
  hasTargetHandle = true,
  sourceHandles,
}: BaseNodeProps) {
  const categoryStyles = {
    trigger: 'border-info bg-info/[.10]',
    action: 'border-success bg-success/[.10]',
    condition: 'border-warning bg-warning/[.10]',
    goal: 'border-info bg-info/[.10]',
  };

  const categoryLabelStyles = {
    trigger: 'bg-primary',
    action: 'bg-success',
    condition: 'bg-warning',
    goal: 'bg-info',
  };

  const isConfigured = data.isConfigured !== false;

  return (
    <div
      className={cn(
        'relative min-w-[200px] rounded-lg border-2 shadow-md transition-shadow',
        categoryStyles[category],
        selected && 'ring-2 ring-offset-2 ring-brand',
        !isConfigured && 'border-dashed opacity-80'
      )}
    >
      {/* Category label */}
      <div
        className={cn(
          'absolute -top-3 left-3 rounded px-2 py-0.5 text-xs font-medium text-white',
          categoryLabelStyles[category]
        )}
      >
        {category.charAt(0).toUpperCase() + category.slice(1)}
      </div>

      {/* Node content */}
      <div className="p-4 pt-5">
        {/* Header with icon */}
        <div className="flex items-center gap-2 mb-2">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full"
            style={{ backgroundColor: color + '20', color }}
          >
            {icon}
          </div>
          <span className="font-medium text-foreground text-sm">{data.label}</span>
        </div>

        {/* Configuration preview */}
        {children && <div className="text-xs text-muted-foreground mt-2">{children}</div>}

        {/* Unconfigured warning */}
        {!isConfigured && (
          <div className="text-xs text-warning mt-2 italic">
            Click to configure
          </div>
        )}
      </div>

      {/* Target handle (input) */}
      {hasTargetHandle && (
        <Handle
          type="target"
          position={Position.Top}
          className="!h-3 !w-3 !bg-muted-foreground !border-2 !border-border"
        />
      )}

      {/* Source handle(s) (output) */}
      {hasSourceHandle && !sourceHandles && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!h-3 !w-3 !bg-muted-foreground !border-2 !border-border"
        />
      )}

      {/* Custom source handles for conditions */}
      {sourceHandles?.map((handle) => (
        <Handle
          key={handle.id}
          type="source"
          position={handle.position}
          id={handle.id}
          className={cn(
            '!h-3 !w-3 !border-2 !border-border',
            handle.id === 'true' ? '!bg-success' : '!bg-destructive'
          )}
          style={{
            left: handle.id === 'true' ? '30%' : '70%',
          }}
        />
      ))}
    </div>
  );
}

export default memo(BaseNode);
