import { DragEvent, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { categoryColor, useNodeCatalog } from '@/hooks/useNodeCatalog';
import { NodeCatalogEntry } from '@/types/workflow';
import { nodeIcon } from './nodeIcons';

function NodePaletteItem({ node }: { node: NodeCatalogEntry }) {
  const onDragStart = (event: DragEvent<HTMLDivElement>) => {
    event.dataTransfer.setData('application/reactflow', node.type);
    event.dataTransfer.setData('nodeLabel', node.label);
    event.dataTransfer.effectAllowed = 'move';
  };

  const color = categoryColor[node.category];
  const categoryStyles = {
    trigger: 'border-info/[.30] hover:border-info/[.50] hover:bg-info/[.10]',
    action: 'border-success/[.30] hover:border-success/[.50] hover:bg-success/[.10]',
    condition: 'border-warning/[.30] hover:border-warning/[.50] hover:bg-warning/[.10]',
  }[node.category];

  return (
    <div
      draggable
      onDragStart={onDragStart}
      title={node.description}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border cursor-grab',
        'transition-all duration-150 active:cursor-grabbing',
        categoryStyles,
      )}
    >
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
        style={{ backgroundColor: `${color}20`, color }}
      >
        {nodeIcon(node.icon)}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-foreground">{node.label}</p>
        <p className="truncate text-xs text-muted-foreground">{node.description}</p>
      </div>
    </div>
  );
}

function Section({ title, nodes }: { title: string; nodes: NodeCatalogEntry[] }) {
  if (nodes.length === 0) return null;
  return (
    <div>
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      <div className="space-y-2">
        {nodes.map((node) => (
          <NodePaletteItem key={node.type} node={node} />
        ))}
      </div>
    </div>
  );
}

export default function NodePalette() {
  const { data: catalog = [], isLoading, error } = useNodeCatalog();
  const [query, setQuery] = useState('');

  const groups = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const matches = needle
      ? catalog.filter(
          (node) =>
            node.label.toLowerCase().includes(needle) ||
            node.description.toLowerCase().includes(needle),
        )
      : catalog;

    return {
      triggers: matches.filter((n) => n.category === 'trigger'),
      actions: matches.filter(
        (n) => n.category === 'action' && n.type !== 'action_goal',
      ),
      conditions: matches.filter((n) => n.category === 'condition'),
      goals: matches.filter((n) => n.type === 'action_goal'),
      total: matches.length,
    };
  }, [catalog, query]);

  if (error) {
    return (
      <p className="p-4 text-sm text-destructive">
        The list of steps could not be loaded. Reload the page to try again.
      </p>
    );
  }

  return (
    <div className="space-y-6 p-4">
      {/* Forty-nine steps is too many to scan, and scrolling past the one you
          want is how people conclude a feature does not exist. */}
      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-8"
          placeholder="Search steps"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading steps&hellip;</p>
      )}

      {!isLoading && groups.total === 0 && (
        <p className="text-sm text-muted-foreground">
          No step matches &ldquo;{query}&rdquo;.
        </p>
      )}

      <Section title="Triggers" nodes={groups.triggers} />
      <Section title="Actions" nodes={groups.actions} />
      <Section title="Logic" nodes={groups.conditions} />
      <Section title="Goals" nodes={groups.goals} />

      {!isLoading && (
        <div className="border-t pt-4">
          <p className="text-center text-xs text-subtle-foreground">
            Drag a step onto the canvas to add it
          </p>
        </div>
      )}
    </div>
  );
}
