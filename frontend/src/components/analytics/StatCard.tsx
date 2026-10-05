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
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
  };

  const trendColor = {
    up: 'text-green-600',
    down: 'text-red-600',
    flat: 'text-gray-500',
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
