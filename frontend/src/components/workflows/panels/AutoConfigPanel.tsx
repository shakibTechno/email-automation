import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { useTags } from '@/hooks/useTags';
import { useSegments } from '@/hooks/useSegments';
import { useTemplates } from '@/hooks/useTemplates';
import { useForms } from '@/hooks/useForms';
import { useSequences } from '@/hooks/useSequences';
import { usePopups } from '@/hooks/usePopups';
import { useWorkflows } from '@/hooks/useWorkflows';
import { useTeamMembers } from '@/hooks/useTeam';
import { NodeCatalogEntry, NodeConfigField } from '@/types/workflow';

/**
 * Settings for a node whose configuration is just a list of fields.
 *
 * Most of the catalogue is like this: pick a tag, type a number, choose a
 * segment. Only the handful with genuinely bespoke UI — a pipeline that
 * filters the stage list beside it, a template picker with a preview — keep a
 * hand-written panel, and the catalogue says which by marking them
 * `ui: 'custom'`.
 *
 * This is deliberately not a form engine. It renders the seven field types
 * the catalogue declares and nothing else.
 */

interface Props {
  spec: NodeCatalogEntry;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

/** What each asset kind offers to choose from. */
function useAssetOptions(kind: string) {
  const { tags } = useTags();
  const { data: segmentData } = useSegments();
  const { templates } = useTemplates();
  const { forms } = useForms();
  const { data: sequenceData } = useSequences();
  const { popups } = usePopups();
  const { data: workflowData } = useWorkflows();
  const { data: members = [] } = useTeamMembers();

  const pick = (): { id: string; label: string }[] => {
    switch (kind) {
      case 'tag':
        return tags.map((t: any) => ({ id: t.id, label: t.name }));
      case 'segment':
        return (segmentData?.results || []).map((s: any) => ({
          id: s.id, label: s.name,
        }));
      case 'email_template':
        return (templates || []).map((t: any) => ({ id: t.id, label: t.name }));
      case 'form':
        return (forms || []).map((f: any) => ({ id: f.id, label: f.name }));
      case 'sequence':
        return (sequenceData?.results || []).map((s: any) => ({
          id: s.id, label: s.name,
        }));
      case 'popup':
        return (popups || []).map((p: any) => ({ id: p.id, label: p.name }));
      case 'workflow':
        return (workflowData?.data || []).map((w: any) => ({
          id: w.id, label: w.name,
        }));
      case 'user':
        return (members || []).map((m: any) => ({
          id: m.id,
          label: m.full_name || m.email,
        }));
      default:
        return [];
    }
  };

  return pick();
}

const EMPTY = '__none__';

function AssetField({
  field, value, onChange,
}: {
  field: NodeConfigField;
  value: string;
  onChange: (value: string) => void;
}) {
  const options = useAssetOptions(field.asset);

  return (
    <div>
      <Label>
        {field.label}
        {field.required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      <Select
        // Radix throws on an empty-string item value, so "nothing chosen" has
        // its own sentinel rather than ''.
        value={value || EMPTY}
        onValueChange={(next) => onChange(next === EMPTY ? '' : next)}
      >
        <SelectTrigger className="mt-1">
          <SelectValue placeholder="Choose one" />
        </SelectTrigger>
        <SelectContent>
          {!field.required && <SelectItem value={EMPTY}>Any</SelectItem>}
          {options.map((option) => (
            <SelectItem key={option.id} value={option.id}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {options.length === 0 && (
        <p className="mt-1 text-xs text-warning">
          Nothing to choose from yet — create one first, or this step will fail
          when a contact reaches it.
        </p>
      )}
      {field.help && (
        <p className="mt-1 text-xs text-muted-foreground">{field.help}</p>
      )}
    </div>
  );
}

export default function AutoConfigPanel({ spec, config, onChange }: Props) {
  const set = (key: string, value: unknown) =>
    onChange({ ...config, [key]: value });

  const visible = spec.config_fields.filter((field) => {
    if (!field.depends_on) return true;
    const other = String(config[field.depends_on.field] ?? '');
    return field.depends_on.values.includes(other);
  });

  if (visible.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        This step has nothing to configure.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {visible.map((field) => {
        const value = config[field.key] ?? field.default ?? '';

        if (field.type === 'asset') {
          return (
            <AssetField
              key={field.key}
              field={field}
              value={String(value ?? '')}
              onChange={(next) => set(field.key, next)}
            />
          );
        }

        if (field.type === 'boolean') {
          return (
            <div key={field.key} className="flex items-start space-x-2">
              <Checkbox
                id={`cfg-${field.key}`}
                checked={Boolean(value)}
                onCheckedChange={(checked) => set(field.key, Boolean(checked))}
              />
              <div>
                <Label htmlFor={`cfg-${field.key}`}>{field.label}</Label>
                {field.help && (
                  <p className="text-xs text-muted-foreground">{field.help}</p>
                )}
              </div>
            </div>
          );
        }

        if (field.type === 'select') {
          return (
            <div key={field.key}>
              <Label>{field.label}</Label>
              <Select
                value={String(value || field.options[0]?.value || EMPTY)}
                onValueChange={(next) => set(field.key, next)}
              >
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {field.options.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {field.help && (
                <p className="mt-1 text-xs text-muted-foreground">{field.help}</p>
              )}
            </div>
          );
        }

        if (field.type === 'textarea') {
          return (
            <div key={field.key}>
              <Label>
                {field.label}
                {field.required && <span className="ml-0.5 text-destructive">*</span>}
              </Label>
              <Textarea
                rows={3}
                className="mt-1"
                value={String(value ?? '')}
                onChange={(event) => set(field.key, event.target.value)}
              />
              {field.help && (
                <p className="mt-1 text-xs text-muted-foreground">{field.help}</p>
              )}
            </div>
          );
        }

        const numeric = field.type === 'number' || field.type === 'duration';
        return (
          <div key={field.key}>
            <Label>
              {field.label}
              {field.required && <span className="ml-0.5 text-destructive">*</span>}
            </Label>
            <Input
              className="mt-1"
              type={numeric ? 'number' : 'text'}
              value={String(value ?? '')}
              onChange={(event) =>
                set(
                  field.key,
                  numeric
                    ? Number(event.target.value || 0)
                    : event.target.value,
                )
              }
            />
            {field.help && (
              <p className="mt-1 text-xs text-muted-foreground">{field.help}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
