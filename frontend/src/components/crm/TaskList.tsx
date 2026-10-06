import { useState } from 'react';
import {
  CheckCircle2,
  Circle,
  Plus,
  Trash2,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TaskFormDialog } from './TaskFormDialog';
import { useTasks, useTaskMutations } from '@/hooks/useCRM';
import { useAuthStore } from '@/stores/authStore';
import { CRMTaskListItem, CreateTaskData, TaskFilters } from '@/types/crm';
import { cn } from '@/lib/utils';

const PRIORITY_CONFIG: Record<string, { label: string; className: string }> = {
  low:    { label: 'Low',    className: 'bg-secondary text-muted-foreground' },
  medium: { label: 'Medium', className: 'bg-info/[.14] text-info' },
  high:   { label: 'High',   className: 'bg-warning/[.14] text-warning' },
  urgent: { label: 'Urgent', className: 'bg-destructive/[.14] text-destructive' },
};


interface TaskItemProps {
  task: CRMTaskListItem;
  onComplete: (id: string) => void;
  onDelete: (id: string) => void;
}

const TaskItem = ({ task, onComplete, onDelete }: TaskItemProps) => {
  const isDone = task.status === 'done';
  const priorityCfg = PRIORITY_CONFIG[task.priority] || PRIORITY_CONFIG.medium;

  return (
    <div
      className={cn(
        'flex items-start gap-3 px-4 py-3 border-b last:border-0',
        task.is_overdue && !isDone && 'bg-destructive/[0.04]',
      )}
    >
      <button
        onClick={() => !isDone && onComplete(task.id)}
        className="mt-0.5 shrink-0 text-muted-foreground hover:text-primary transition-colors"
        disabled={isDone}
      >
        {isDone ? (
          <CheckCircle2 className="h-5 w-5 text-success" />
        ) : (
          <Circle className="h-5 w-5" />
        )}
      </button>

      <div className="flex-1 min-w-0">
        <p className={cn('text-sm font-medium', isDone && 'line-through text-muted-foreground')}>
          {task.title}
        </p>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span className={cn('text-xs px-1.5 py-0.5 rounded font-medium', priorityCfg.className)}>
            {priorityCfg.label}
          </span>
          {task.due_date && (
            <span
              className={cn(
                'flex items-center gap-1 text-xs',
                task.is_overdue && !isDone ? 'text-destructive font-medium' : 'text-muted-foreground'
              )}
            >
              {task.is_overdue && !isDone
                ? <AlertCircle className="h-3 w-3" />
                : <Clock className="h-3 w-3" />
              }
              {new Date(task.due_date).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
              })}
            </span>
          )}
          {task.assigned_to_name && (
            <span className="text-xs text-muted-foreground truncate">
              → {task.assigned_to_name}
            </span>
          )}
        </div>
      </div>

      <Button
        variant="ghost"
        size="sm"
        className="shrink-0 h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
        onClick={() => onDelete(task.id)}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
};

interface TaskListProps {
  dealId?: string;
  contactId?: string;
  filters?: TaskFilters;
  showAddButton?: boolean;
}

export const TaskList = ({ dealId, contactId, filters = {}, showAddButton = true }: TaskListProps) => {
  const [showForm, setShowForm] = useState(false);
  const [myTasksOnly, setMyTasksOnly] = useState(false);
  const currentUser = useAuthStore((s) => s.user);

  const combinedFilters: TaskFilters = {
    ...filters,
    ...(dealId ? { deal: dealId } : {}),
    ...(contactId ? { contact: contactId } : {}),
    ...(myTasksOnly && currentUser ? { assigned_to: currentUser.id } : {}),
  };

  const { data: tasks = [], isLoading } = useTasks(combinedFilters);
  const { createTask, completeTask, deleteTask, isCreating } = useTaskMutations();

  const handleCreate = async (data: CreateTaskData) => {
    await createTask(data);
    setShowForm(false);
  };

  if (isLoading) {
    return <div className="py-8 text-center text-sm text-muted-foreground">Loading tasks...</div>;
  }

  return (
    <div>
      {showAddButton && (
        <div className="px-4 py-2 border-b flex items-center justify-between">
          <Button variant="ghost" size="sm" className="gap-1 text-xs" onClick={() => setShowForm(true)}>
            <Plus className="h-3.5 w-3.5" />
            Add Task
          </Button>
          {!dealId && !contactId && (
            <Button
              variant={myTasksOnly ? 'default' : 'ghost'}
              size="sm"
              className="text-xs"
              onClick={() => setMyTasksOnly(!myTasksOnly)}
            >
              My Tasks
            </Button>
          )}
        </div>
      )}

      {tasks.length === 0 ? (
        <div className="py-8 text-center text-sm text-muted-foreground">
          No tasks yet
        </div>
      ) : (
        tasks.map(task => (
          <TaskItem
            key={task.id}
            task={task}
            onComplete={completeTask}
            onDelete={deleteTask}
          />
        ))
      )}

      <TaskFormDialog
        open={showForm}
        onOpenChange={setShowForm}
        onSubmit={handleCreate}
        isLoading={isCreating}
        dealId={dealId}
        contactId={contactId}
      />
    </div>
  );
};
