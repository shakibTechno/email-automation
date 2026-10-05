import { Card, CardContent } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { TrendIndicator } from '@/types/analytics';

interface StatCardProps {
  title: string;
  trend: TrendIndicator;
  icon: React.ElementType;
  format?: (value: number) => string;
  color?: 'blue' | 'green' | 'purple' | 'orange';
}

export function StatCard({
  title,
  trend,
  icon: Icon,
  format,
  color = 'blue',
}: StatCardProps) {
  const colorClasses = {
    blue: 'bg-info/[.14] text-info',
    green: 'bg-success/[.14] text-success',
    purple: 'bg-info/[.14] text-info',
    orange: 'bg-warning/[.14] text-warning',
  };

  const trendColor = {
    up: 'text-success',
    down: 'text-destructive',
    flat: 'text-muted-foreground',
  };

  const TrendIcon = {
    up: TrendingUp,
    down: TrendingDown,
    flat: Minus,
  }[trend.direction];

  const displayValue = format ? format(trend.value) : trend.value.toLocaleString();

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-2">{displayValue}</p>
            <div className={`flex items-center gap-1 mt-2 text-sm ${trendColor[trend.direction]}`}>
              <TrendIcon className="h-4 w-4" />
              <span>{trend.change_percent}%</span>
              <span className="text-muted-foreground ml-1">vs prev. period</span>
            </div>
          </div>
          <div className={`rounded-lg p-3 ${colorClasses[color]}`}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
