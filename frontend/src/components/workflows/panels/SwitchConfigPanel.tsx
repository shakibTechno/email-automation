import { useState } from 'react';
import { ChevronDown, ChevronRight, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import RuleEditor, { Rule } from './RuleEditor';

/**
 * Split by Rule: several named paths, first match wins.
 *
 * Each path's name is what the canvas edge carries, which is how a fifth path
 * costs a config entry rather than a new edge type in the database. Renaming
 * a path therefore orphans the edge drawn from it, so the panel says so
 * instead of letting it be found out later.
 */

interface Branch {
  name: string;
  rules: Rule[];
  logic: 'all' | 'any';
}

interface Props {
  config: { branches?: Branch[] };
  label: string;
  onChange: (config: Record<string, unknown>) => void;
  onLabelChange: (label: string) => void;
}

export default function SwitchConfigPanel({
  config, label, onChange, onLabelChange,
}: Props) {
  const branches: Branch[] = config.branches || [];
  const [open, setOpen] = useState<number | null>(branches.length ? 0 : null);

  const set = (next: Branch[]) => onChange({ ...config, branches: next });

  const update = (index: number, partial: Partial<Branch>) =>
    set(branches.map((b, i) => (i === index ? { ...b, ...partial } : b)));

  const add = () => {
    set([
      ...branches,
      { name: `Path ${branches.length + 1}`, rules: [], logic: 'all' },
    ]);
    setOpen(branches.length);
  };

  const remove = (index: number) => {
    set(branches.filter((_, i) => i !== index));
    setOpen(null);
  };

  const duplicateNames = branches
    .map((b) => b.name.trim().toLowerCase())
    .filter((name, index, all) => name && all.indexOf(name) !== index);

  return (
    <div className="space-y-5">
      <div>
        <Label>Step label</Label>
        <Input
          className="mt-1"
          value={label || ''}
          onChange={(event) => onLabelChange(event.target.value)}
          placeholder="Route by plan"
        />
      </div>

      <div className="space-y-2">
        <Label>Paths</Label>
        <p className="text-xs text-muted-foreground">
          Checked top to bottom; the first one that matches wins. Anyone
          matching none takes the fallback.
        </p>

        {branches.length === 0 ? (
          <div className="rounded-lg border border-dashed py-5 text-center">
            <p className="mb-3 text-sm text-muted-foreground">
              No paths yet — every contact would take the fallback.
            </p>
            <Button variant="outline" size="sm" onClick={add}>
              <Plus className="mr-2 h-4 w-4" />
              Add a path
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            {branches.map((branch, index) => {
              const isOpen = open === index;
              return (
                <div key={index} className="rounded-lg border">
                  <div className="flex items-center gap-2 p-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 shrink-0"
                      onClick={() => setOpen(isOpen ? null : index)}
                    >
                      {isOpen ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </Button>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {index + 1}
                    </span>
                    <Input
                      value={branch.name}
                      placeholder="Path name"
                      onChange={(event) =>
                        update(index, { name: event.target.value })
                      }
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 shrink-0"
                      onClick={() => remove(index)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </div>

                  {isOpen && (
                    <div className="border-t p-3">
                      <RuleEditor
                        title={`Take "${branch.name || 'this path'}" when`}
                        rules={branch.rules || []}
                        logic={branch.logic || 'all'}
                        onChange={(rules, logic) =>
                          update(index, { rules, logic })
                        }
                      />
                      {(branch.rules || []).length === 0 && (
                        <p className="mt-2 text-xs text-warning">
                          A path with no conditions matches everyone, so no
                          path below it can ever be reached.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={add}
            >
              <Plus className="mr-2 h-4 w-4" />
              Add a path
            </Button>
          </div>
        )}
      </div>

      {duplicateNames.length > 0 && (
        <p className="rounded-md border border-destructive/40 bg-destructive/[.08] p-3 text-xs">
          Two paths share a name. The canvas identifies a path by its name, so
          contacts matching either would all follow whichever edge was drawn
          first.
        </p>
      )}

      <div className="space-y-2 rounded-lg bg-secondary/60 p-3">
        <p className="text-sm font-medium">On the canvas</p>
        <div className="space-y-1 text-xs text-muted-foreground">
          <p>
            Draw one edge per path, plus one for{' '}
            <strong className="text-foreground">fallback</strong>. A contact
            reaching a path with nothing after it stops there.
          </p>
          <p>
            Renaming a path here does not move the edge already drawn from it —
            reconnect it after a rename.
          </p>
        </div>
      </div>
    </div>
  );
}
