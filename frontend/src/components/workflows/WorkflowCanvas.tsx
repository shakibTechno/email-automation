import { useCallback, useRef, DragEvent } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  Connection,
  addEdge,
  ReactFlowInstance,
  BackgroundVariant,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { nodeTypes } from './nodes';
import { WorkflowNodeType, getNodeTypeInfo } from '@/types/workflow';

interface WorkflowCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: (nodes: Node[]) => void;
  onEdgesChange: (edges: Edge[]) => void;
  onNodeClick?: (node: Node) => void;
  readOnly?: boolean;
}

let nodeIdCounter = 0;
const getId = () => `node_${Date.now()}_${nodeIdCounter++}`;

export default function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onNodeClick,
  readOnly = false,
}: WorkflowCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);

  // Handle node changes from React Flow (drag, select, etc.)
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const updatedNodes = applyNodeChanges(changes, nodes);
      onNodesChange(updatedNodes);
    },
    [nodes, onNodesChange]
  );

  // Handle edge changes from React Flow
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const updatedEdges = applyEdgeChanges(changes, edges);
      onEdgesChange(updatedEdges);
    },
    [edges, onEdgesChange]
  );

  // Handle new connections
  const handleConnect = useCallback(
    (params: Connection) => {
      // Determine edge type based on source handle
      const edgeType =
        params.sourceHandle === 'true'
          ? 'true'
          : params.sourceHandle === 'false'
          ? 'false'
          : 'default';

      const newEdge = {
        ...params,
        id: `edge_${Date.now()}`,
        type: 'smoothstep',
        data: { edgeType },
        animated: edgeType !== 'default',
        style: {
          stroke:
            edgeType === 'true'
              ? '#22c55e'
              : edgeType === 'false'
              ? '#ef4444'
              : '#94a3b8',
          strokeWidth: 2,
        },
      };

      const updatedEdges = addEdge(newEdge, edges);
      onEdgesChange(updatedEdges);
    },
    [edges, onEdgesChange]
  );

  // Handle drag & drop from palette
  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();

      if (!reactFlowWrapper.current || !reactFlowInstance.current) return;

      const type = event.dataTransfer.getData(
        'application/reactflow'
      ) as WorkflowNodeType;
      const label = event.dataTransfer.getData('nodeLabel');

      if (!type) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.current.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      const nodeInfo = getNodeTypeInfo(type);

      const newNode: Node = {
        id: getId(),
        type,
        position,
        data: {
          label: label || nodeInfo?.label || type,
          node_type: type,
          config: {},
        },
      };

      onNodesChange([...nodes, newNode]);
    },
    [nodes, onNodesChange]
  );

  const handleInit = useCallback((instance: ReactFlowInstance) => {
    reactFlowInstance.current = instance;
  }, []);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node);
    },
    [onNodeClick]
  );

  return (
    <div ref={reactFlowWrapper} className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        onInit={handleInit}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={!readOnly}
        defaultEdgeOptions={{
          type: 'smoothstep',
          style: { stroke: '#94a3b8', strokeWidth: 2 },
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Controls showInteractive={!readOnly} />
        <MiniMap
          nodeStrokeWidth={3}
          nodeColor={(node) => {
            const type = node.type || '';
            if (type.startsWith('trigger_')) return '#3b82f6';
            if (type.startsWith('action_')) return '#22c55e';
            if (type.startsWith('condition_')) return '#f59e0b';
            return '#94a3b8';
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
      </ReactFlow>
    </div>
  );
}
