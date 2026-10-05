import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, GripVertical } from 'lucide-react';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { usePipelines, usePipeline, usePipelineMutations } from '@/hooks/useCRM';
import { StageType } from '@/types/crm';

const STAGE_COLORS = [
  '#6366f1', '#8b5cf6', '#a855f7', '#ec4899', '#f43f5e',
  '#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6',
  '#06b6d4', '#3b82f6', '#6b7280',
];

export const PipelineSettingsPage = () => {
  const navigate = useNavigate();
  const { data: pipelines } = usePipelines();
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>('');

  useEffect(() => {
    if (pipelines && pipelines.length > 0 && !selectedPipelineId) {
      const def = pipelines.find(p => p.is_default) || pipelines[0];
      setSelectedPipelineId(def.id);
    }
  }, [pipelines, selectedPipelineId]);

  const { data: pipeline, isLoading } = usePipeline(selectedPipelineId);
  const {
    updatePipeline, addStage, removeStage, reorderStages,
    isUpdating,
  } = usePipelineMutations();

  const [pipelineName, setPipelineName] = useState('');
  const [pipelineDesc, setPipelineDesc] = useState('');
  const [showAddStage, setShowAddStage] = useState(false);
  const [newStageName, setNewStageName] = useState('');
  const [newStageColor, setNewStageColor] = useState('#6366f1');
  const [newStageType, setNewStageType] = useState<StageType>('open');
  const [newStageProbability, setNewStageProbability] = useState('50');

  useEffect(() => {
    if (pipeline) {
      setPipelineName(pipeline.name);
      setPipelineDesc(pipeline.description);
    }
  }, [pipeline]);

  const handleSavePipeline = async () => {
    await updatePipeline(selectedPipelineId, {
      name: pipelineName,
      description: pipelineDesc,
    });
  };

  const handleAddStage = async () => {
    await addStage(selectedPipelineId, {
      name: newStageName,
      color: newStageColor,
      stage_type: newStageType,
      default_probability: parseInt(newStageProbability),
    });
    setShowAddStage(false);
    setNewStageName('');
    setNewStageColor('#6366f1');
    setNewStageType('open');
    setNewStageProbability('50');
  };

  const handleRemoveStage = async (stageId: string) => {
    if (window.confirm('Are you sure you want to remove this stage?')) {
      try {
        await removeStage(selectedPipelineId, stageId);
      } catch {
        // Error handled by mutation
      }
    }
  };

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination || !pipeline) return;

    const stages = [...pipeline.stages].sort((a, b) => a.position - b.position);
    const [moved] = stages.splice(result.source.index, 1);
    stages.splice(result.destination.index, 0, moved);

    reorderStages(selectedPipelineId, stages.map(s => s.id));
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const sortedStages = pipeline ? [...pipeline.stages].sort((a, b) => a.position - b.position) : [];

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/crm')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-2xl font-bold">Pipeline Settings</h1>
      </div>

      {/* Pipeline selector */}
      {pipelines && pipelines.length > 1 && (
        <Select value={selectedPipelineId} onValueChange={setSelectedPipelineId}>
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Select pipeline" />
          </SelectTrigger>
          <SelectContent>
            {pipelines.map(p => (
              <SelectItem key={p.id} value={p.id}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {/* Pipeline info */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="pName">Name</Label>
            <Input
              id="pName"
              value={pipelineName}
              onChange={(e) => setPipelineName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="pDesc">Description</Label>
            <Textarea
              id="pDesc"
              value={pipelineDesc}
              onChange={(e) => setPipelineDesc(e.target.value)}
              rows={2}
            />
          </div>
          <Button onClick={handleSavePipeline} disabled={isUpdating}>
            {isUpdating ? 'Saving...' : 'Save Changes'}
          </Button>
        </CardContent>
      </Card>

      {/* Stages */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Stages</CardTitle>
          <Button size="sm" onClick={() => setShowAddStage(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Add Stage
          </Button>
        </CardHeader>
        <CardContent>
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="stages">
              {(provided) => (
                <div
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                  className="space-y-2"
                >
                  {sortedStages.map((stage, index) => (
                    <Draggable key={stage.id} draggableId={stage.id} index={index}>
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          className={`flex items-center gap-3 p-3 bg-white border rounded-lg ${
                            snapshot.isDragging ? 'shadow-lg' : ''
                          }`}
                        >
                          <div {...provided.dragHandleProps} className="cursor-grab">
                            <GripVertical className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <div
                            className="h-4 w-4 rounded-full shrink-0"
                            style={{ backgroundColor: stage.color }}
                          />
                          <div className="flex-1">
                            <div className="text-sm font-medium">{stage.name}</div>
                            <div className="text-xs text-muted-foreground">
                              {stage.stage_type === 'open' ? 'Open' : stage.stage_type === 'won' ? 'Won' : 'Lost'}
                              {' '}&middot; {stage.default_probability}% probability
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveStage(stage.id)}
                            className="text-red-500 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        </CardContent>
      </Card>

      {/* Add Stage Dialog */}
      <Dialog open={showAddStage} onOpenChange={setShowAddStage}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Stage</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={newStageName}
                onChange={(e) => setNewStageName(e.target.value)}
                placeholder="e.g. Discovery"
              />
            </div>

            <div className="space-y-2">
              <Label>Color</Label>
              <div className="flex gap-2 flex-wrap">
                {STAGE_COLORS.map(color => (
                  <button
                    key={color}
                    type="button"
                    onClick={() => setNewStageColor(color)}
                    className={`h-7 w-7 rounded-full border-2 transition-all ${
                      newStageColor === color ? 'border-gray-900 scale-110' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={newStageType} onValueChange={(v) => setNewStageType(v as StageType)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="won">Won</SelectItem>
                    <SelectItem value="lost">Lost</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Default Probability (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={newStageProbability}
                  onChange={(e) => setNewStageProbability(e.target.value)}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddStage(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddStage} disabled={!newStageName}>
              Add Stage
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
