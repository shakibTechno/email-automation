import { useState } from 'react';
import { X } from 'lucide-react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  EdgeProps,
  getSmoothStepPath,
  useReactFlow,
} from 'reactflow';

/**
 * A connection you can actually remove.
 *
 * Before this, the only way to delete one was to click the 2px line and press
 * Backspace. Three things made that effectively impossible:
 *
 *   * React Flow's `deleteKeyCode` defaults to Backspace alone, so Delete —
 *     which is what people press — did nothing
 *   * the edge's stroke was set as an inline style, and an inline style beats
 *     the stylesheet rule React Flow uses to show an edge as selected, so a
 *     selected edge looked identical to an unselected one
 *   * nothing on screen suggested an edge could be selected in the first place
 *
 * So the line is now hoverable, shows a cross, and the colour comes from the
 * branch rather than from a hardcoded inline style.
 */

/** Branch colours, matching the handles on ConditionNode. */
const BRANCH_COLOURS: Record<string, string> = {
  true: '#22c55e',
  met: '#22c55e',
  a: '#3b82f6',
  false: '#ef4444',
  timeout: '#ef4444',
  b: '#a855f7',
  fallback: '#64748b',
};

const DEFAULT_COLOUR = '#94a3b8';

export default function DeletableEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}: EdgeProps) {
  const { setEdges } = useReactFlow();
  const [hovered, setHovered] = useState(false);

  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const branch = (data?.edgeType as string) || 'default';
  const colour = BRANCH_COLOURS[branch] || DEFAULT_COLOUR;
  const active = selected || hovered;

  const remove = () =>
    // Through React Flow's own store so the change flows out through
    // onEdgesChange like any other edit, and the workflow is marked dirty.
    setEdges((edges) => edges.filter((edge) => edge.id !== id));

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={{
          stroke: active ? colour : colour,
          strokeWidth: active ? 3 : 2,
          // Selection needs to be visible or the keyboard shortcut is a
          // guess. No inline stroke override, so the stylesheet still wins.
          filter: active ? `drop-shadow(0 0 3px ${colour})` : undefined,
        }}
      />

      {/* A wide invisible path, so the line is as easy to hit as it looks. */}
      <path
        d={path}
        fill="none"
        strokeWidth={22}
        stroke="transparent"
        style={{ cursor: 'pointer' }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />

      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          className="nodrag nopan"
        >
          {branch !== 'default' && (
            <span
              className="mr-1 rounded px-1.5 py-0.5 text-[10px] font-medium capitalize"
              style={{ backgroundColor: `${colour}22`, color: colour }}
            >
              {branch}
            </span>
          )}

          <button
            type="button"
            aria-label="Remove this connection"
            title="Remove this connection"
            onClick={remove}
            className={[
              'inline-flex h-5 w-5 items-center justify-center rounded-full',
              'border bg-background text-muted-foreground shadow-sm',
              'transition-opacity hover:border-destructive hover:text-destructive',
              active ? 'opacity-100' : 'opacity-0',
            ].join(' ')}
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
