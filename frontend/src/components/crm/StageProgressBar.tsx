import { cn } from '@/lib/utils';
import { Stage } from '@/types/crm';

interface StageProgressBarProps {
  stages: Stage[];
  currentStageId: string;
}

export const StageProgressBar = ({ stages, currentStageId }: StageProgressBarProps) => {
  const sortedStages = [...stages].sort((a, b) => a.position - b.position);
  const currentIndex = sortedStages.findIndex(s => s.id === currentStageId);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1">
        {sortedStages.map((stage, index) => {
          const isPast = index < currentIndex;
          const isCurrent = index === currentIndex;
          return (
            <div key={stage.id} className="flex-1">
              <div
                className={cn(
                  'h-2 rounded-full transition-colors',
                  isPast ? 'bg-primary' : isCurrent ? 'bg-primary' : 'bg-gray-200'
                )}
                style={isPast || isCurrent ? { backgroundColor: stage.color } : undefined}
              />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{sortedStages[0]?.name}</span>
        <span>{sortedStages[sortedStages.length - 1]?.name}</span>
      </div>
    </div>
  );
};
