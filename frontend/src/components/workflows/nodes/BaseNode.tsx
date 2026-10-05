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
    trigger: 'border-blue-500 bg-blue-50',
    action: 'border-green-500 bg-green-50',
    condition: 'border-amber-500 bg-amber-50',
    goal: 'border-purple-500 bg-purple-50',
  };

  const categoryLabelStyles = {
    trigger: 'bg-blue-500',
    action: 'bg-green-500',
    condition: 'bg-amber-500',
    goal: 'bg-purple-500',
  };

  const isConfigured = data.isConfigured !== false;

  return (
    <div
      className={cn(
        'relative min-w-[200px] rounded-lg border-2 shadow-md transition-shadow',
        categoryStyles[category],
        selected && 'ring-2 ring-offset-2 ring-blue-500',
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
          <span className="font-medium text-gray-900 text-sm">{data.label}</span>
        </div>

        {/* Configuration preview */}
        {children && <div className="text-xs text-gray-600 mt-2">{children}</div>}

        {/* Unconfigured warning */}
        {!isConfigured && (
          <div className="text-xs text-amber-600 mt-2 italic">
            Click to configure
          </div>
        )}
      </div>

      {/* Target handle (input) */}
      {hasTargetHandle && (
        <Handle
          type="target"
          position={Position.Top}
          className="!h-3 !w-3 !bg-gray-400 !border-2 !border-white"
        />
      )}

      {/* Source handle(s) (output) */}
      {hasSourceHandle && !sourceHandles && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!h-3 !w-3 !bg-gray-400 !border-2 !border-white"
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
            '!h-3 !w-3 !border-2 !border-white',
            handle.id === 'true' ? '!bg-green-500' : '!bg-red-500'
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
