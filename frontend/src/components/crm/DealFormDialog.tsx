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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ContactSearchSelect } from './ContactSearchSelect';
import { MemberSelect } from './MemberSelect';
import { Stage, CreateDealData, Deal, DealPriority } from '@/types/crm';

interface DealFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pipelineId: string;
  stages: Stage[];
  onSubmit: (data: CreateDealData) => void;
  isLoading?: boolean;
  initialData?: Partial<Deal>;
  defaultStageId?: string;
  defaultContactId?: string;
}

export const DealFormDialog = ({
  open,
  onOpenChange,
  pipelineId,
  stages,
  onSubmit,
  isLoading,
  initialData,
  defaultStageId,
  defaultContactId,
}: DealFormDialogProps) => {
  const openStages = stages.filter(s => s.stage_type === 'open');

  const [title, setTitle] = useState('');
  const [stageId, setStageId] = useState('');
  const [value, setValue] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [probability, setProbability] = useState('');
  const [priority, setPriority] = useState<DealPriority>('medium');
  const [closeDate, setCloseDate] = useState('');
  const [description, setDescription] = useState('');
  const [primaryContact, setPrimaryContact] = useState<string | null>(null);
  const [assignedTo, setAssignedTo] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      const firstOpenStage = stages.find(s => s.stage_type === 'open');
      setTitle(initialData?.title || '');
      setStageId(initialData?.stage || defaultStageId || firstOpenStage?.id || '');
      setValue(initialData?.value?.toString() || '');
      setCurrency(initialData?.currency || 'USD');
      setProbability(initialData?.probability?.toString() || '');
      setPriority((initialData?.priority as DealPriority) || 'medium');
      setCloseDate(initialData?.close_date || '');
      setDescription(initialData?.description || '');
      setPrimaryContact(initialData?.primary_contact || defaultContactId || null);
      setAssignedTo(initialData?.assigned_to || null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const selectedStage = stages.find(s => s.id === stageId);

    onSubmit({
      title,
      description,
      pipeline: pipelineId,
      stage: stageId || undefined,
      value: value ? parseFloat(value) : 0,
      currency,
      probability: probability ? parseInt(probability) : selectedStage?.default_probability,
      priority,
      close_date: closeDate || null,
      primary_contact: primaryContact,
      assigned_to: assignedTo,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {initialData ? 'Edit Deal' : 'Create New Deal'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Deal Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Enterprise contract - Acme Corp"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="stage">Stage</Label>
              <Select value={stageId} onValueChange={setStageId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select stage" />
                </SelectTrigger>
                <SelectContent>
                  {openStages.map(stage => (
                    <SelectItem key={stage.id} value={stage.id}>
                      {stage.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="priority">Priority</Label>
              <Select value={priority} onValueChange={(v) => setPriority(v as DealPriority)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="value">Deal Value</Label>
              <div className="flex gap-2">
                <Input
                  id="value"
                  type="number"
                  min="0"
                  step="0.01"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder="0.00"
                  className="flex-1"
                />
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger className="w-20">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="EUR">EUR</SelectItem>
                    <SelectItem value="GBP">GBP</SelectItem>
                    <SelectItem value="BRL">BRL</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="probability">Probability (%)</Label>
              <Input
                id="probability"
                type="number"
                min="0"
                max="100"
                value={probability}
                onChange={(e) => setProbability(e.target.value)}
                placeholder="Auto from stage"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="closeDate">Expected Close Date</Label>
            <Input
              id="closeDate"
              type="date"
              value={closeDate}
              onChange={(e) => setCloseDate(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label>Primary Contact</Label>
            <ContactSearchSelect
              value={primaryContact}
              onChange={setPrimaryContact}
            />
          </div>

          <div className="space-y-2">
            <Label>Assigned To</Label>
            <MemberSelect value={assignedTo} onChange={setAssignedTo} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Deal details..."
              rows={3}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!title || isLoading}>
              {isLoading ? 'Saving...' : initialData ? 'Update Deal' : 'Create Deal'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
