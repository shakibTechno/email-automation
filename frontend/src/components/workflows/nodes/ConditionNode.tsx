import { memo } from 'react';
import { NodeProps, Position } from 'reactflow';
import BaseNode, { BaseNodeData } from './BaseNode';
import { GitBranch } from 'lucide-react';
import { ConditionRule } from '@/types/workflow';

interface ConditionNodeData extends BaseNodeData {
  node_type: 'condition_if_else';
  config: {
    rules?: ConditionRule[];
    logic?: 'all' | 'any';
  };
}

function ConditionNode(props: NodeProps<ConditionNodeData>) {
  const { data } = props;
  const config = data.config || {};
  const rules = config.rules || [];
  const logic = config.logic || 'all';

  const isConfigured = rules.length > 0;

  const getConfigPreview = () => {
    if (rules.length === 0) return null;

    return (
      <div className="space-y-1">
        <span className="text-gray-500">
          {rules.length} condition{rules.length !== 1 ? 's' : ''} ({logic === 'all' ? 'AND' : 'OR'})
        </span>
        <div className="flex gap-2 text-[10px] mt-1">
          <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
            True
          </span>
          <span className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded">
            False
          </span>
        </div>
      </div>
    );
  };

  return (
    <BaseNode
      {...props}
      data={{ ...data, isConfigured }}
      icon={<GitBranch className="h-4 w-4" />}
      color="#f59e0b"
      category="condition"
      hasSourceHandle={false}
      sourceHandles={[
        { id: 'true', position: Position.Bottom, label: 'True' },
        { id: 'false', position: Position.Bottom, label: 'False' },
      ]}
    >
      {getConfigPreview()}
    </BaseNode>
  );
}

export default memo(ConditionNode);
