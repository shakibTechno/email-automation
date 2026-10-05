import { Node } from 'reactflow';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WorkflowNodeType, TriggerNodeType, ActionNodeType, getNodeTypeInfo } from '@/types/workflow';
import TriggerConfigPanel from './TriggerConfigPanel';
import ActionConfigPanel from './ActionConfigPanel';
import ConditionConfigPanel from './ConditionConfigPanel';

interface NodeConfigPanelProps {
  node: Node;
  onClose: () => void;
  onUpdate: (nodeId: string, data: Record<string, unknown>) => void;
  onDelete: (nodeId: string) => void;
}

export default function NodeConfigPanel({
  node,
  onClose,
  onUpdate,
  onDelete,
}: NodeConfigPanelProps) {
  const nodeType = node.type as WorkflowNodeType;
  const nodeInfo = getNodeTypeInfo(nodeType);

  const handleConfigChange = (config: Record<string, unknown>) => {
    onUpdate(node.id, {
      ...node.data,
      config,
    });
  };

  const handleLabelChange = (label: string) => {
    onUpdate(node.id, {
      ...node.data,
      label,
    });
  };

  const renderConfigPanel = () => {
    if (nodeType.startsWith('trigger_')) {
      return (
        <TriggerConfigPanel
          nodeType={nodeType as TriggerNodeType}
          config={node.data.config || {}}
          label={node.data.label}
          onChange={handleConfigChange}
          onLabelChange={handleLabelChange}
        />
      );
    }

    if (nodeType.startsWith('action_')) {
      return (
        <ActionConfigPanel
          nodeType={nodeType as ActionNodeType}
          config={node.data.config || {}}
          label={node.data.label}
          onChange={handleConfigChange}
          onLabelChange={handleLabelChange}
        />
      );
    }

    if (nodeType.startsWith('condition_')) {
      return (
        <ConditionConfigPanel
          config={node.data.config || {}}
          label={node.data.label}
          onChange={handleConfigChange}
          onLabelChange={handleLabelChange}
        />
      );
    }

    return <p className="text-muted-foreground">No configuration available</p>;
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div>
          <h3 className="font-semibold">{nodeInfo?.label || 'Configure Node'}</h3>
          <p className="text-xs text-muted-foreground">{nodeInfo?.description}</p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Config content */}
      <div className="flex-1 overflow-y-auto p-4">{renderConfigPanel()}</div>

      {/* Footer */}
      <div className="border-t p-4">
        <Button
          variant="destructive"
          className="w-full"
          onClick={() => {
            onDelete(node.id);
            onClose();
          }}
        >
          Delete Node
        </Button>
      </div>
    </div>
  );
}
