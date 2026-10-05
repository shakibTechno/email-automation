import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Phone, Mail, Video, CheckSquare, StickyNote } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ActivityType, CreateActivityData } from '@/types/crm';
import { MemberSelect } from './MemberSelect';

const activityTypes: { type: ActivityType; label: string; icon: React.ElementType }[] = [
  { type: 'call', label: 'Call', icon: Phone },
  { type: 'email', label: 'Email', icon: Mail },
  { type: 'meeting', label: 'Meeting', icon: Video },
  { type: 'task', label: 'Task', icon: CheckSquare },
  { type: 'note', label: 'Note', icon: StickyNote },
];

interface ActivityFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: CreateActivityData) => void;
  isLoading?: boolean;
  dealId?: string;
  contactId?: string;
}

export const ActivityFormDialog = ({
  open,
  onOpenChange,
  onSubmit,
  isLoading,
  dealId,
  contactId,
}: ActivityFormDialogProps) => {
  const [activityType, setActivityType] = useState<ActivityType>('note');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [duration, setDuration] = useState('');
  const [assignedTo, setAssignedTo] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setActivityType('note');
      setTitle('');
      setDescription('');
      setDueDate('');
      setDuration('');
      setAssignedTo(null);
    }
  }, [open]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      activity_type: activityType,
      title,
      description,
      deal: dealId || null,
      contact: contactId || null,
      due_date: dueDate || null,
      duration: duration ? parseInt(duration) : null,
      assigned_to: assignedTo,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Log Activity</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>Activity Type</Label>
            <div className="flex gap-2">
              {activityTypes.map(({ type, label, icon: Icon }) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setActivityType(type)}
                  className={cn(
                    'flex flex-col items-center gap-1 px-3 py-2 rounded-md border text-xs transition-colors',
                    activityType === type
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-gray-200 text-muted-foreground hover:border-gray-300'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="actTitle">Title *</Label>
            <Input
              id="actTitle"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Follow-up call with client"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="actDescription">Description</Label>
            <Textarea
              id="actDescription"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Notes about this activity..."
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="actDueDate">Due Date</Label>
              <Input
                id="actDueDate"
                type="datetime-local"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="actDuration">Duration (minutes)</Label>
              <Input
                id="actDuration"
                type="number"
                min="0"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                placeholder="30"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Assigned To</Label>
            <MemberSelect value={assignedTo} onChange={setAssignedTo} />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!title || isLoading}>
              {isLoading ? 'Saving...' : 'Log Activity'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
