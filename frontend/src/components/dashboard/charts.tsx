import { cn } from '@/lib/utils';

/**
 * Small, dependency-free chart primitives for the dashboard.
 *
 * They all take a plain number[] and stretch to their container, so a card can
 * stay responsive without a chart library. Recharts is still used on the
 * Analytics pages where axes and tooltips actually matter — these are for the
 * glanceable tiles, where a library would be weight without benefit.
 */

const VIEW_W = 160;

/** Maps values onto the viewBox. A flat series must not divide by zero. */
const toPoints = (values: number[], height: number, pad = 3): Array<[number, number]> => {
  if (values.length === 0) return [];
  if (values.length === 1) return [[0, height / 2], [VIEW_W, height / 2]];

  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const step = VIEW_W / (values.length - 1);

  return values.map((v, i) => [
    i * step,
    pad + (1 - (v - min) / span) * (height - pad * 2),
  ]);
};

const linePath = (pts: Array<[number, number]>) =>
  pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');

const peakIndex = (values: number[]) =>
  values.reduce((best, v, i) => (v > values[best] ? i : best), 0);

/** No data is a state, not a hole: a flat dashed rule keeps the tile's shape. */
const FlatBaseline = ({ height, label }: { height: number; label?: string }) => (
  <div
    className="flex items-center justify-center"
    style={{ height }}
    aria-label={label ?? 'No data for this period'}
  >
    <span className="h-px w-full border-t border-dashed border-border" />
  </div>
);

interface SeriesProps {
  values: number[];
  className?: string;
  height?: number;
}

/** Dotted line with a glowing marker on the peak — the contacts tile. */
export const DottedSparkline = ({ values, className, height = 44 }: SeriesProps) => {
  const pts = toPoints(values, height);
  if (pts.length === 0) return <FlatBaseline height={height} />;
  const peak = pts[peakIndex(values)];

  return (
    <svg
      className={cn('w-full overflow-visible', className)}
      style={{ height }}
      viewBox={`0 0 ${VIEW_W} ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d={linePath(pts)}
        fill="none"
        stroke="hsl(var(--brand))"
        strokeWidth="1.6"
        strokeDasharray="3 3"
        vectorEffect="non-scaling-stroke"
      />
      <circle cx={peak[0]} cy={peak[1]} r="3.4" fill="hsl(var(--brand))" />
      <circle cx={peak[0]} cy={peak[1]} r="7" fill="hsl(var(--brand))" opacity=".2" />
    </svg>
  );
};

/** Vertical hairlines — the sends tile. */
export const StickChart = ({ values, className, height = 44 }: SeriesProps) => {
  const pts = toPoints(values, height);
  if (pts.length === 0) return <FlatBaseline height={height} />;
  const peak = pts[peakIndex(values)];

  return (
    <svg
      className={cn('w-full overflow-visible', className)}
      style={{ height }}
      viewBox={`0 0 ${VIEW_W} ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {pts.map(([x, y], i) => (
        <path
          key={i}
          d={`M${x.toFixed(1)},${height} V${y.toFixed(1)}`}
          stroke="hsl(var(--muted-foreground))"
          strokeWidth="1.4"
          opacity=".55"
          vectorEffect="non-scaling-stroke"
        />
      ))}
      <circle cx={peak[0]} cy={peak[1]} r="3" fill="hsl(var(--brand))" />
    </svg>
  );
};

/** Dense lime ticks — the rate tiles. Pure CSS, no SVG needed. */
export const TickBars = ({ values, className, height = 44 }: SeriesProps) => {
  if (values.length === 0) return <FlatBaseline height={height} />;
  const max = Math.max(...values) || 1;

  return (
    <div className={cn('tick-row', className)} style={{ height }} aria-hidden="true">
      {values.map((v, i) => (
        <i key={i} style={{ height: `${Math.max(8, (v / max) * 100)}%` }} />
      ))}
    </div>
  );
};

/** Smooth arc — the value tile. */
export const AreaSparkline = ({ values, className, height = 44 }: SeriesProps) => {
  const pts = toPoints(values, height);
  if (pts.length === 0) return <FlatBaseline height={height} />;
  const peak = pts[peakIndex(values)];

  return (
    <svg
      className={cn('w-full overflow-visible', className)}
      style={{ height }}
      viewBox={`0 0 ${VIEW_W} ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d={linePath(pts)}
        fill="none"
        stroke="hsl(var(--brand))"
        strokeWidth="1.8"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      <circle cx={peak[0]} cy={peak[1]} r="3.4" fill="hsl(var(--brand))" />
      <circle cx={peak[0]} cy={peak[1]} r="7" fill="hsl(var(--brand))" opacity=".2" />
    </svg>
  );
};

interface HeroChartProps {
  values: number[];
  labels?: string[];
  height?: number;
  gradientId?: string;
}

/** The featured card's filled curve, with the glow under it. */
export const HeroAreaChart = ({
  values,
  labels = [],
  height = 170,
  gradientId = 'hero-fill',
}: HeroChartProps) => {
  const W = 620;
  const pts = (() => {
    if (values.length === 0) return [];
    if (values.length === 1) return [[0, height / 2], [W, height / 2]] as Array<[number, number]>;
    const max = Math.max(...values);
    const min = Math.min(...values);
    const span = max - min || 1;
    const step = W / (values.length - 1);
    return values.map((v, i) => [
      i * step,
      6 + (1 - (v - min) / span) * (height - 12),
    ]) as Array<[number, number]>;
  })();

  if (pts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-6">
        <span className="h-px w-full border-t border-dashed border-border" />
        <span className="text-[12.5px] text-subtle-foreground">
          No activity in this period yet.
        </span>
      </div>
    );
  }

  const line = linePath(pts);
  const peak = pts[peakIndex(values)];

  return (
    <>
      <svg
        className="w-full overflow-visible"
        style={{ height }}
        viewBox={`0 0 ${W} ${height}`}
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--brand))" stopOpacity=".30" />
            <stop offset="100%" stopColor="hsl(var(--brand))" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${line} L${W},${height} L0,${height} Z`} fill={`url(#${gradientId})`} />
        <path
          d={line}
          fill="none"
          stroke="hsl(var(--brand))"
          strokeWidth="2"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
        <circle cx={peak[0]} cy={peak[1]} r="4.5" fill="hsl(var(--brand))" />
        <circle cx={peak[0]} cy={peak[1]} r="11" fill="hsl(var(--brand))" opacity=".22" />
      </svg>

      {labels.length > 0 && (
        <div className="mt-2 flex justify-between font-mono text-[10px] text-subtle-foreground">
          {labels.map((l, i) => (
            <span key={i}>{l}</span>
          ))}
        </div>
      )}
    </>
  );
};

interface BarGroupProps {
  values: number[];
  labels?: string[];
  height?: number;
}

/** Grouped bars with the tallest highlighted. */
export const BarGroup = ({ values, labels = [], height = 100 }: BarGroupProps) => {
  if (values.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-4">
        <span className="h-px w-full border-t border-dashed border-border" />
        <span className="text-[12.5px] text-subtle-foreground">Nothing to chart yet.</span>
      </div>
    );
  }
  const max = Math.max(...values) || 1;
  const peak = peakIndex(values);

  return (
    <>
      <div className="flex items-end gap-1.5" style={{ height }} aria-hidden="true">
        {values.map((v, i) => (
          <i
            key={i}
            className={cn(
              'block flex-1 rounded-t-[3px]',
              i === peak ? 'bg-brand-fill' : 'bg-secondary'
            )}
            style={{ height: `${Math.max(4, (v / max) * 100)}%` }}
          />
        ))}
      </div>
      {labels.length > 0 && (
        <div className="mt-2 flex justify-between font-mono text-[10px] text-subtle-foreground">
          {labels.map((l, i) => (
            <span key={i}>{l}</span>
          ))}
        </div>
      )}
    </>
  );
};
