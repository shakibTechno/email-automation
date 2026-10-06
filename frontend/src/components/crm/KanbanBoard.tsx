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
      <div className="flex gap-3 overflow-x-auto pb-3 min-h-[calc(100vh-320px)]">
        {columns.map((column) => (
          <div
            key={column.stage.id}
            className="flex flex-col rounded-xl border bg-secondary/40 min-w-[264px] w-[264px] shrink-0"
          >
            {/* Column header */}
            <div className="px-3 py-2.5 border-b">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div
                    className="h-2 w-2 rounded-full flex-none"
                    style={{ backgroundColor: column.stage.color }}
                  />
                  <h3 className="text-[12.5px] font-bold tracking-tight text-foreground">
                    {column.stage.name}
                  </h3>
                  <span className="ml-auto font-mono text-[10.5px] text-subtle-foreground">
                    {column.deal_count}
                  </span>
                </div>
              </div>
              {Number(column.total_value) > 0 && (
                <div className="font-mono text-[11px] text-brand">
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
                    snapshot.isDraggingOver ? 'bg-info/[0.05]' : ''
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
              <div className="p-2 border-t border-border">
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
