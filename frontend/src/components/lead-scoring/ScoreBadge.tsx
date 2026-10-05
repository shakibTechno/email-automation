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
  high: 'bg-red-100 text-red-700 border-red-200 hover:bg-red-200',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-200 hover:bg-yellow-200',
  low: 'bg-blue-100 text-blue-700 border-blue-200 hover:bg-blue-200',
  none: 'bg-gray-100 text-gray-600 border-gray-200 hover:bg-gray-200',
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
