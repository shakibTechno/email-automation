import { useState } from 'react';
import { useFormAnalytics } from '@/hooks/useAnalytics';
import { AnalyticsTabNav } from './AnalyticsOverviewPage';
import { DateRangeSelector } from '@/components/analytics/DateRangeSelector';
import { ChartCard } from '@/components/analytics/ChartCard';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export function FormAnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useFormAnalytics(days);

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">Form submission analytics</p>
        </div>
        <DateRangeSelector value={days} onChange={setDays} />
      </div>

      <AnalyticsTabNav />

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Submissions over time */}
          <ChartCard title="Submissions Over Time">
            <div className="h-[300px]">
              {data.submissions_over_time.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.submissions_over_time}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      className="text-xs"
                    />
                    <YAxis className="text-xs" />
                    <Tooltip labelFormatter={(v) => new Date(v).toLocaleDateString()} />
                    <Area
                      type="monotone"
                      dataKey="count"
                      name="Submissions"
                      stroke="#a855f7"
                      fill="#a855f740"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-muted-foreground py-10">No submissions in this period</p>
              )}
            </div>
          </ChartCard>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top forms bar chart */}
            <ChartCard title="Top Forms">
              <div className="h-[300px]">
                {data.top_forms.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.top_forms} layout="vertical" margin={{ left: 120 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis type="number" className="text-xs" />
                      <YAxis
                        dataKey="name"
                        type="category"
                        width={110}
                        className="text-xs"
                        tickFormatter={(v) => v.length > 18 ? v.slice(0, 18) + '...' : v}
                      />
                      <Tooltip />
                      <Bar dataKey="submissions" name="Submissions" fill="#a855f7" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted-foreground py-10">No form data</p>
                )}
              </div>
            </ChartCard>

            {/* Forms table */}
            <Card>
              <div className="p-4">
                <h3 className="text-base font-semibold mb-3">All Forms</h3>
                <div className="overflow-y-auto max-h-[280px]">
                  <table className="w-full text-sm">
                    <thead className="border-b text-muted-foreground sticky top-0 bg-background">
                      <tr>
                        <th className="text-left py-2 font-medium">Form</th>
                        <th className="text-left py-2 font-medium">Status</th>
                        <th className="text-right py-2 font-medium">Submissions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data.form_metrics.map((f) => (
                        <tr key={f.id}>
                          <td className="py-2 font-medium">{f.name}</td>
                          <td className="py-2">
                            <Badge variant={f.status === 'active' ? 'default' : 'secondary'}>
                              {f.status}
                            </Badge>
                          </td>
                          <td className="py-2 text-right">{f.submissions}</td>
                        </tr>
                      ))}
                      {data.form_metrics.length === 0 && (
                        <tr>
                          <td colSpan={3} className="py-6 text-center text-muted-foreground">
                            No forms found
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </Card>
          </div>
        </div>
      ) : null}
    </div>
  );
}
