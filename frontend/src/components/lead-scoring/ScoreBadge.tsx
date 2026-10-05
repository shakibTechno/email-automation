import { Badge } from '@/components/ui/badge';
import { TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Props {
  score: number;
  engagementLevel?: string;
  onClick?: () => void;
  className?: string;
}

const LEVEL_STYLES: Record<string, string> = {
  high: 'bg-destructive/[.14] text-destructive border-destructive/[.30] hover:bg-destructive/[.30]',
  medium: 'bg-warning/[.14] text-warning border-warning/[.30] hover:bg-warning/[.30]',
  low: 'bg-info/[.14] text-info border-info/[.30] hover:bg-info/[.30]',
  none: 'bg-secondary text-muted-foreground border-border hover:bg-secondary',
};

const LEVEL_LABELS: Record<string, string> = {
  high: 'Hot',
  medium: 'Warm',
  low: 'Cold',
  none: 'Inactive',
};

export function ScoreBadge({ score, engagementLevel = 'none', onClick, className }: Props) {
  const style = LEVEL_STYLES[engagementLevel] ?? LEVEL_STYLES.none;
  const label = LEVEL_LABELS[engagementLevel] ?? 'Inactive';

  return (
    <Badge
      variant="outline"
      onClick={onClick}
      className={cn(
        style,
        'gap-1.5 font-semibold select-none',
        onClick && 'cursor-pointer transition-colors',
        className
      )}
    >
      <TrendingUp className="h-3 w-3" />
      {score} · {label}
    </Badge>
  );
}
