import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { useCreateScoringRule, useUpdateScoringRule } from '@/hooks/useLeadScoring';
import type { ScoringRule, ScoringRuleFormData } from '@/types/leadScoring';

const DEMOGRAPHIC_FIELDS = [
  { value: 'email',       label: 'Email' },
  { value: 'first_name',  label: 'First Name' },
  { value: 'last_name',   label: 'Last Name' },
  { value: 'company',     label: 'Company' },
  { value: 'job_title',   label: 'Job Title' },
  { value: 'phone',       label: 'Phone' },
  { value: 'is_subscribed', label: 'Is Subscribed' },
  { value: 'lead_score',  label: 'Lead Score' },
];

const STRING_OPERATORS = [
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Does not equal' },
  { value: 'contains', label: 'Contains' },
  { value: 'not_contains', label: 'Does not contain' },
  { value: 'starts_with', label: 'Starts with' },
  { value: 'ends_with', label: 'Ends with' },
  { value: 'is_empty', label: 'Is empty' },
  { value: 'is_not_empty', label: 'Is not empty' },
];

const NUMBER_OPERATORS = [
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Does not equal' },
  { value: 'greater_than', label: 'Greater than' },
  { value: 'less_than', label: 'Less than' },
  { value: 'greater_or_equal', label: 'Greater or equal' },
  { value: 'less_or_equal', label: 'Less or equal' },
];

const BOOLEAN_OPERATORS = [
  { value: 'is_true', label: 'Is true' },
  { value: 'is_false', label: 'Is false' },
];

const EVENT_TYPES = [
  { value: 'email_opened',       label: 'Email Opened' },
  { value: 'email_clicked',      label: 'Email Clicked' },
  { value: 'form_submitted',     label: 'Form Submitted' },
  { value: 'tag_added',          label: 'Tag Added' },
  { value: 'tag_removed',        label: 'Tag Removed' },
  { value: 'workflow_completed', label: 'Workflow Completed' },
  { value: 'unsubscribed',       label: 'Unsubscribed' },
  { value: 'bounced',            label: 'Bounced' },
];

function getOperators(field: string) {
  if (field === 'is_subscribed') return BOOLEAN_OPERATORS;
  if (field === 'lead_score') return NUMBER_OPERATORS;
  return STRING_OPERATORS;
}

function valueInputNeeded(operator: string) {
  return !['is_empty', 'is_not_empty', 'is_true', 'is_false'].includes(operator);
}

interface Props {
  open: boolean;
  onClose: () => void;
  editRule?: ScoringRule | null;
}

type FormValues = {
  name: string;
  description: string;
  rule_type: 'demographic' | 'behavioral';
  points: number;
  is_active: boolean;
  condition_field: string;
  condition_operator: string;
  condition_value: string;
  event_type: string;
};

export function ScoringRuleForm({ open, onClose, editRule }: Props) {
  const create = useCreateScoringRule();
  const update = useUpdateScoringRule();

  const { register, handleSubmit, watch, setValue, reset, formState: { errors } } =
    useForm<FormValues>({
      defaultValues: {
        name: '',
        description: '',
        rule_type: 'demographic',
        points: 10,
        is_active: true,
        condition_field: 'company',
        condition_operator: 'is_not_empty',
        condition_value: '',
        event_type: 'email_opened',
      },
    });

  useEffect(() => {
    if (editRule) {
      reset({
        name: editRule.name,
        description: editRule.description ?? '',
        rule_type: editRule.rule_type,
        points: editRule.points,
        is_active: editRule.is_active,
        condition_field: editRule.condition?.field ?? 'company',
        condition_operator: editRule.condition?.operator ?? 'is_not_empty',
        condition_value: String(editRule.condition?.value ?? ''),
        event_type: editRule.event_type ?? 'email_opened',
      });
    } else {
      reset();
    }
  }, [editRule, reset]);

  const ruleType = watch('rule_type');
  const condField = watch('condition_field');
  const condOp = watch('condition_operator');
  const operators = getOperators(condField);
  const showValue = valueInputNeeded(condOp);

  function onSubmit(values: FormValues) {
    const payload: ScoringRuleFormData = {
      name: values.name,
      description: values.description,
      rule_type: values.rule_type,
      points: Number(values.points),
      is_active: values.is_active,
    };

    if (values.rule_type === 'demographic') {
      payload.condition = {
        field: values.condition_field,
        operator: values.condition_operator as any,
        value: values.condition_value,
      };
    } else {
      payload.event_type = values.event_type as any;
    }

    if (editRule) {
      update.mutate({ id: editRule.id, data: payload }, { onSuccess: onClose });
    } else {
      create.mutate(payload, { onSuccess: onClose });
    }
  }

  const isPending = create.isPending || update.isPending;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{editRule ? 'Edit Rule' : 'New Scoring Rule'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="name">Rule Name</Label>
            <Input
              id="name"
              {...register('name', { required: 'Name is required' })}
              placeholder="e.g. Has Company"
            />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea id="description" {...register('description')} rows={2} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Rule Type</Label>
              <Select value={ruleType} onValueChange={(v) => setValue('rule_type', v as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="demographic">Demographic</SelectItem>
                  <SelectItem value="behavioral">Behavioral</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="points">Points (+/-)</Label>
              <Input
                id="points"
                type="number"
                {...register('points', { required: true, valueAsNumber: true })}
              />
            </div>
          </div>

          {ruleType === 'demographic' ? (
            <div className="space-y-3 rounded-lg border p-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Condition</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Field</Label>
                  <Select
                    value={condField}
                    onValueChange={(v) => {
                      setValue('condition_field', v);
                      setValue('condition_operator', getOperators(v)[0].value);
                    }}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {DEMOGRAPHIC_FIELDS.map((f) => (
                        <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Operator</Label>
                  <Select
                    value={condOp}
                    onValueChange={(v) => setValue('condition_operator', v)}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {operators.map((o) => (
                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {showValue && (
                <div className="space-y-1.5">
                  <Label>Value</Label>
                  <Input
                    {...register('condition_value')}
                    placeholder="Comparison value"
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-1.5">
              <Label>Event Type</Label>
              <Select
                value={watch('event_type')}
                onValueChange={(v) => setValue('event_type', v)}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {EVENT_TYPES.map((e) => (
                    <SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="flex items-center gap-3">
            <Switch
              id="is_active"
              checked={watch('is_active')}
              onCheckedChange={(v) => setValue('is_active', v)}
            />
            <Label htmlFor="is_active">Active</Label>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving…' : editRule ? 'Update Rule' : 'Create Rule'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
