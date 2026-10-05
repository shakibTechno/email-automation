import { Phone, Mail, Video, CheckSquare, StickyNote, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ActivityListItem, ActivityType } from '@/types/crm';

const typeConfig: Record<ActivityType, { icon: React.ElementType; color: string }> = {
  call: { icon: Phone, color: 'bg-blue-100 text-blue-600' },
  email: { icon: Mail, color: 'bg-purple-100 text-purple-600' },
  meeting: { icon: Video, color: 'bg-green-100 text-green-600' },
  task: { icon: CheckSquare, color: 'bg-yellow-100 text-yellow-600' },
  note: { icon: StickyNote, color: 'bg-gray-100 text-gray-600' },
};

const timeAgo = (dateStr: string) => {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

interface ActivityTimelineProps {
  activities: ActivityListItem[];
  onComplete?: (id: string) => void;
  onLogActivity?: () => void;
  isCompacting?: boolean;
}

export const ActivityTimeline = ({
  activities,
  onComplete,
  onLogActivity,
  isCompacting,
}: ActivityTimelineProps) => {
  return (
    <div className="space-y-4">
      {onLogActivity && (
        <Button size="sm" onClick={onLogActivity}>
          Log Activity
        </Button>
      )}

      {activities.length === 0 ? (
        <p className="text-sm text-muted-foreground">No activities yet.</p>
      ) : (
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />

          <div className="space-y-4">
            {activities.map((activity) => {
              const config = typeConfig[activity.activity_type] || typeConfig.note;
              const Icon = config.icon;

              return (
                <div key={activity.id} className="relative flex gap-3 pl-0">
                  <div
                    className={cn(
                      'relative z-10 flex items-center justify-center w-8 h-8 rounded-full shrink-0',
                      config.color
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className={cn(
                        'text-sm font-medium truncate',
                        activity.is_completed && 'line-through text-muted-foreground'
                      )}>
                        {activity.title}
                      </h4>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-xs text-muted-foreground">
                          {timeAgo(activity.created_at)}
                        </span>
                        {!activity.is_completed && onComplete && (
                          <button
                            onClick={() => onComplete(activity.id)}
                            className="text-muted-foreground hover:text-green-600 transition-colors"
                            title="Mark as completed"
                          >
                            <Check className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {!isCompacting && activity.description && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {activity.description}
                      </p>
                    )}

                    {activity.created_by_name && !isCompacting && (
                      <p className="text-xs text-muted-foreground mt-1">
                        by {activity.created_by_name}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
