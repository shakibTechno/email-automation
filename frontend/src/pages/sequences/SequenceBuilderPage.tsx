import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { ArrowLeft, Plus, Trash2, GripVertical, Clock, Mail } from 'lucide-react';
import { useSequence, useSequenceMutations, useStepMutations } from '@/hooks/useSequences';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import type { CreateSequenceData, SequenceStep } from '@/types/sequence';

interface StepDialogState {
  open: boolean;
  step: SequenceStep | null;
}

export default function SequenceBuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data: sequence, isLoading } = useSequence(id || '');
  const { create, update } = useSequenceMutations();
  const { createStep, updateStep, deleteStep } = useStepMutations(id || '');

  const [form, setForm] = useState<CreateSequenceData>({
    name: '',
    description: '',
    sender_name: '',
    sender_email: '',
    reply_to_email: '',
    allow_reenrollment: false,
  });

  const [stepDialog, setStepDialog] = useState<StepDialogState>({ open: false, step: null });
  const [stepForm, setStepForm] = useState({
    subject: '',
    template: '',
    delay_days: 0,
    delay_hours: 0,
  });

  // Templates for step configuration
  const { data: templatesData } = useQuery({
    queryKey: ['templates-list'],
    queryFn: async () => {
      const { data } = await apiClient.get('/templates');
      return data;
    },
  });
  const templates = templatesData?.results || templatesData || [];

  useEffect(() => {
    if (sequence) {
      setForm({
        name: sequence.name,
        description: sequence.description,
        sender_name: sequence.sender_name,
        sender_email: sequence.sender_email,
        reply_to_email: sequence.reply_to_email,
        allow_reenrollment: sequence.allow_reenrollment,
      });
    }
  }, [sequence]);

  const handleSave = async () => {
    if (!form.name.trim()) return;
    if (isEdit && id) {
      await update.mutateAsync({ id, data: form });
      navigate(`/sequences/${id}`);
    } else {
      const seq = await create.mutateAsync(form);
      navigate(`/sequences/${seq.id}/edit`);
    }
  };

  const openNewStep = () => {
    setStepForm({ subject: '', template: '', delay_days: 0, delay_hours: 0 });
    setStepDialog({ open: true, step: null });
  };

  const openEditStep = (step: SequenceStep) => {
    setStepForm({
      subject: step.subject,
      template: step.template || '',
      delay_days: step.delay_days,
      delay_hours: step.delay_hours,
    });
    setStepDialog({ open: true, step });
  };

  const handleSaveStep = async () => {
    if (!stepForm.subject.trim() || !id) return;
    if (stepDialog.step) {
      await updateStep.mutateAsync({
        id: stepDialog.step.id,
        data: {
          subject: stepForm.subject,
          template: stepForm.template || null,
          delay_days: stepForm.delay_days,
          delay_hours: stepForm.delay_hours,
        },
      });
    } else {
      await createStep.mutateAsync({
        sequence: id,
        subject: stepForm.subject,
        template: stepForm.template || undefined,
        delay_days: stepForm.delay_days,
        delay_hours: stepForm.delay_hours,
      });
    }
    setStepDialog({ open: false, step: null });
  };

  const handleDeleteStep = async (stepId: string) => {
    if (confirm('Delete this step?')) {
      await deleteStep.mutateAsync(stepId);
    }
  };

  const steps = sequence?.steps || [];

  if (isEdit && isLoading) {
    return <div className="p-6 text-muted-foreground">Loading...</div>;
  }

  return (
    <div className="w-full space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate('/sequences')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{isEdit ? 'Edit Sequence' : 'New Sequence'}</h1>
        </div>
      </div>

      {/* Sequence Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Sequence Settings</CardTitle>
          <CardDescription>Configure the basic settings for your email sequence.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label>Name *</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g., Welcome Onboarding Series"
              />
            </div>
            <div className="col-span-2">
              <Label>Description</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="What does this sequence do?"
                rows={2}
              />
            </div>
            <div>
              <Label>Sender Name</Label>
              <Input
                value={form.sender_name}
                onChange={(e) => setForm({ ...form, sender_name: e.target.value })}
                placeholder="Your Name or Company"
              />
            </div>
            <div>
              <Label>Sender Email</Label>
              <Input
                type="email"
                value={form.sender_email}
                onChange={(e) => setForm({ ...form, sender_email: e.target.value })}
                placeholder="hello@yourcompany.com"
              />
            </div>
            <div>
              <Label>Reply-To Email</Label>
              <Input
                type="email"
                value={form.reply_to_email}
                onChange={(e) => setForm({ ...form, reply_to_email: e.target.value })}
                placeholder="Optional"
              />
            </div>
            <div className="flex items-center gap-3 pt-6">
              <Switch
                checked={form.allow_reenrollment}
                onCheckedChange={(v) => setForm({ ...form, allow_reenrollment: v })}
              />
              <div>
                <p className="text-sm font-medium">Allow Re-enrollment</p>
                <p className="text-xs text-muted-foreground">Contacts who completed can enroll again</p>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => navigate('/sequences')}>Cancel</Button>
            <Button onClick={handleSave} disabled={!form.name.trim()}>
              {isEdit ? 'Save Changes' : 'Create Sequence'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Steps — only shown when editing an existing sequence */}
      {isEdit && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Steps</CardTitle>
                <CardDescription>
                  Each step sends an email after the specified delay from the previous step.
                </CardDescription>
              </div>
              <Button size="sm" onClick={openNewStep}>
                <Plus className="h-4 w-4 mr-2" />
                Add Step
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {steps.length === 0 ? (
              <div className="text-center py-10 border-2 border-dashed rounded-lg">
                <Mail className="h-10 w-10 mx-auto text-subtle-foreground mb-3" />
                <p className="text-sm text-muted-foreground">No steps yet. Add your first email step.</p>
                <Button size="sm" className="mt-3" onClick={openNewStep}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Step
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {steps.map((step, idx) => (
                  <div
                    key={step.id}
                    className="flex items-start gap-3 p-4 border rounded-lg bg-card hover:border-info/[.30] transition-colors"
                  >
                    <GripVertical className="h-5 w-5 text-subtle-foreground mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-subtle-foreground uppercase">
                          Step {idx + 1}
                        </span>
                        {step.delay_days > 0 || step.delay_hours > 0 ? (
                          <span className="inline-flex items-center gap-1 text-xs text-brand bg-info/[.10] px-2 py-0.5 rounded-full">
                            <Clock className="h-3 w-3" />
                            Wait {step.delay_days > 0 ? `${step.delay_days}d ` : ''}{step.delay_hours > 0 ? `${step.delay_hours}h` : ''}
                          </span>
                        ) : (
                          <span className="text-xs text-success bg-success/[.10] px-2 py-0.5 rounded-full">
                            Immediate
                          </span>
                        )}
                      </div>
                      <p className="font-medium text-foreground mt-1 truncate">{step.subject}</p>
                      {step.template_name && (
                        <p className="text-xs text-muted-foreground">Template: {step.template_name}</p>
                      )}
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <Button variant="ghost" size="sm" onClick={() => openEditStep(step)}>
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        onClick={() => handleDeleteStep(step.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step Dialog */}
      <Dialog open={stepDialog.open} onOpenChange={(o) => !o && setStepDialog({ open: false, step: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{stepDialog.step ? 'Edit Step' : 'Add Step'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>Subject *</Label>
              <Input
                value={stepForm.subject}
                onChange={(e) => setStepForm({ ...stepForm, subject: e.target.value })}
                placeholder="Email subject line"
              />
            </div>
            <div>
              <Label>Email Template</Label>
              <Select
                value={stepForm.template}
                onValueChange={(v) => setStepForm({ ...stepForm, template: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a template" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">No template</SelectItem>
                  {templates.map((t: any) => (
                    <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Delay (Days)</Label>
                <Input
                  type="number"
                  min={0}
                  value={stepForm.delay_days}
                  onChange={(e) => setStepForm({ ...stepForm, delay_days: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div>
                <Label>Delay (Hours)</Label>
                <Input
                  type="number"
                  min={0}
                  max={23}
                  value={stepForm.delay_hours}
                  onChange={(e) => setStepForm({ ...stepForm, delay_hours: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Delay is from the previous step (or enrollment time for the first step).
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStepDialog({ open: false, step: null })}>Cancel</Button>
            <Button onClick={handleSaveStep} disabled={!stepForm.subject.trim()}>
              {stepDialog.step ? 'Save Step' : 'Add Step'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
