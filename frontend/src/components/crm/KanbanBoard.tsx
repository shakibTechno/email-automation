import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { KanbanStage } from '@/types/crm';
import { DealCard } from './DealCard';

interface KanbanBoardProps {
  columns: KanbanStage[];
  onDragEnd: (dealId: string, toStageId: string, newIndex: number) => void;
  onAddDeal?: (stageId: string) => void;
}

const formatValue = (value: number) => {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
};

export const KanbanBoard = ({ columns, onDragEnd, onAddDeal }: KanbanBoardProps) => {
  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return;

    const dealId = result.draggableId;
    const toStageId = result.destination.droppableId;
    const newIndex = result.destination.index;

    onDragEnd(dealId, toStageId, newIndex);
  };

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4 min-h-[calc(100vh-280px)]">
        {columns.map((column) => (
          <div
            key={column.stage.id}
            className="flex flex-col bg-gray-50 rounded-lg min-w-[300px] w-[300px] shrink-0"
          >
            {/* Column header */}
            <div className="p-3 border-b border-gray-200">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: column.stage.color }}
                  />
                  <h3 className="text-sm font-semibold text-gray-900">
                    {column.stage.name}
                  </h3>
                  <span className="text-xs text-muted-foreground bg-gray-200 rounded-full px-1.5 py-0.5">
                    {column.deal_count}
                  </span>
                </div>
              </div>
              {Number(column.total_value) > 0 && (
                <div className="text-xs text-muted-foreground">
                  {formatValue(Number(column.total_value))}
                </div>
              )}
            </div>

            {/* Droppable area */}
            <Droppable droppableId={column.stage.id}>
              {(provided, snapshot) => (
                <div
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                  className={`flex-1 p-2 space-y-2 overflow-y-auto ${
                    snapshot.isDraggingOver ? 'bg-blue-50/50' : ''
                  }`}
                  style={{ minHeight: '100px' }}
                >
                  {column.deals.map((deal, index) => (
                    <Draggable
                      key={deal.id}
                      draggableId={deal.id}
                      index={index}
                    >
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          {...provided.dragHandleProps}
                          className={snapshot.isDragging ? 'opacity-90 rotate-1' : ''}
                        >
                          <DealCard deal={deal} />
                        </div>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>

            {/* Add deal footer */}
            {column.stage.stage_type === 'open' && onAddDeal && (
              <div className="p-2 border-t border-gray-200">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-muted-foreground"
                  onClick={() => onAddDeal(column.stage.id)}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Add deal
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </DragDropContext>
  );
};
