import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Node, Edge } from 'reactflow';
import WorkflowCanvas from '@/components/workflows/WorkflowCanvas';
import WorkflowToolbar from '@/components/workflows/WorkflowToolbar';
import NodePalette from '@/components/workflows/NodePalette';
import { NodeConfigPanel } from '@/components/workflows/panels';
import WorkflowValidationDialog from '@/components/workflows/dialogs/WorkflowValidationDialog';
import { useWorkflow, useWorkflowMutations } from '@/hooks/useWorkflows';
import { workflowsApi } from '@/api/workflows';
import { WorkflowValidation, WorkflowNodeInput, WorkflowEdgeInput } from '@/types/workflow';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

export default function WorkflowBuilderPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isNew = !id || id === 'new';

  // Track the actual workflow ID (changes after first save)
  const [workflowId, setWorkflowId] = useState<string | null>(isNew ? null : id!);

  const { data: workflow, isLoading } = useWorkflow(workflowId || undefined);
  const { createWorkflow, updateWorkflow } = useWorkflowMutations();

  // Local state
  const [name, setName] = useState('Untitled Workflow');
  const [description, setDescription] = useState('');
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const [validation, setValidation] = useState<WorkflowValidation | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  // Load workflow data
  useEffect(() => {
    if (workflow) {
      setName(workflow.name);
      setDescription(workflow.description);

      // Convert backend nodes to React Flow nodes
      const rfNodes: Node[] = workflow.nodes.map((node) => ({
        id: node.id,
        type: node.node_type,
        position: { x: node.position_x, y: node.position_y },
        data: {
          label: node.label || node.node_type,
          node_type: node.node_type,
          config: node.config,
        },
      }));

      // Convert backend edges to React Flow edges
      const rfEdges: Edge[] = workflow.edges.map((edge) => ({
        id: edge.id,
        source: edge.source_node,
        target: edge.target_node,
        sourceHandle: edge.source_handle,
        targetHandle: edge.target_handle,
        type: 'smoothstep',
        animated: edge.edge_type !== 'default',
        data: { edgeType: edge.edge_type },
        style: {
          stroke:
            edge.edge_type === 'true'
              ? '#22c55e'
              : edge.edge_type === 'false'
              ? '#ef4444'
              : '#94a3b8',
          strokeWidth: 2,
        },
      }));

      setNodes(rfNodes);
      setEdges(rfEdges);
      setHasChanges(false);
    }
  }, [workflow]);

  const handleNodesChange = useCallback((newNodes: Node[]) => {
    setNodes(newNodes);
    setHasChanges(true);
  }, []);

  const handleEdgesChange = useCallback((newEdges: Edge[]) => {
    setEdges(newEdges);
    setHasChanges(true);
  }, []);

  const handleNodeClick = useCallback((node: Node) => {
    setSelectedNode(node);
  }, []);

  const handleNodeUpdate = useCallback(
    (nodeId: string, data: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((node) => (node.id === nodeId ? { ...node, data } : node))
      );
      // Also update selectedNode if it's the one being edited
      setSelectedNode((prev) =>
        prev?.id === nodeId ? { ...prev, data } : prev
      );
      setHasChanges(true);
    },
    []
  );

  const handleNodeDelete = useCallback((nodeId: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) =>
      eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId)
    );
    setSelectedNode(null);
    setHasChanges(true);
  }, []);

  const handleSave = async () => {
    // Convert React Flow nodes to backend format
    const nodeInputs: WorkflowNodeInput[] = nodes.map((node) => ({
      id: node.id,
      node_type: node.type as any,
      position_x: node.position.x,
      position_y: node.position.y,
      config: node.data.config || {},
      label: node.data.label || '',
    }));

    // Convert React Flow edges to backend format
    const edgeInputs: WorkflowEdgeInput[] = edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle || 'default',
      targetHandle: edge.targetHandle || 'default',
      type: (edge.data?.edgeType as any) || 'default',
    }));

    const payload = {
      name,
      description,
      nodes: nodeInputs,
      edges: edgeInputs,
    };

    try {
      if (!workflowId) {
        // Create new workflow
        const newWorkflow = await createWorkflow.mutateAsync(payload);
        setWorkflowId(newWorkflow.id);
        navigate(`/workflows/${newWorkflow.id}/edit`, { replace: true });
      } else {
        // Update existing workflow
        await updateWorkflow.mutateAsync({ id: workflowId, data: payload });
      }
      setHasChanges(false);
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleValidate = async () => {
    if (!workflowId) {
      setValidation({
        is_valid: false,
        errors: ['Please save the workflow first before validating.'],
      });
      setShowValidation(true);
      return;
    }

    setIsValidating(true);
    setShowValidation(true);

    try {
      const result = await workflowsApi.validateWorkflow(workflowId);
      setValidation(result);
    } catch (error) {
      setValidation({
        is_valid: false,
        errors: ['Failed to validate workflow.'],
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleActivate = async () => {
    if (!workflowId || hasChanges) return;

    try {
      await workflowsApi.activateWorkflow(workflowId);
      window.location.reload(); // Refresh to update status
    } catch (error: any) {
      const errors = error.response?.data?.errors || ['Failed to activate workflow'];
      setValidation({ is_valid: false, errors });
      setShowValidation(true);
    }
  };

  const handleDeactivate = async () => {
    if (!workflowId) return;

    try {
      await workflowsApi.deactivateWorkflow(workflowId);
      window.location.reload();
    } catch (error) {
      // Error will be shown via toast
    }
  };

  if (isLoading && workflowId) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-info" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Toolbar */}
      <WorkflowToolbar
        workflowName={name}
        status={workflow?.status || 'draft'}
        isSaving={createWorkflow.isPending || updateWorkflow.isPending}
        hasChanges={hasChanges}
        onSave={handleSave}
        onValidate={handleValidate}
        onActivate={handleActivate}
        onDeactivate={handleDeactivate}
        onBack={() => navigate('/workflows')}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar - Node Palette */}
        <div className="w-60 border-r bg-sidebar overflow-y-auto">
          <div className="p-4 border-b space-y-4">
            <div>
              <Label>Name</Label>
              <Input
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setHasChanges(true);
                }}
                placeholder="Workflow name"
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  setHasChanges(true);
                }}
                placeholder="Optional description"
                rows={2}
              />
            </div>
          </div>
          <NodePalette />
        </div>

        {/* Center - Canvas */}
        <div className="flex-1 canvas-grid">
          <WorkflowCanvas
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onNodeClick={handleNodeClick}
          />
        </div>

        {/* Right sidebar - Node Config */}
        {selectedNode && (
          <div className="w-80 border-l">
            <NodeConfigPanel
              node={selectedNode}
              onClose={() => setSelectedNode(null)}
              onUpdate={handleNodeUpdate}
              onDelete={handleNodeDelete}
            />
          </div>
        )}
      </div>

      {/* Validation Dialog */}
      <WorkflowValidationDialog
        open={showValidation}
        onOpenChange={setShowValidation}
        validation={validation}
        isLoading={isValidating}
      />
    </div>
  );
}
