import { useState } from 'react';
import { useLandingPageAnalytics } from '@/hooks/useAnalytics';
import { AnalyticsTabNav } from './AnalyticsOverviewPage';
import { DateRangeSelector } from '@/components/analytics/DateRangeSelector';
import { ChartCard } from '@/components/analytics/ChartCard';
import { Card, CardContent } from '@/components/ui/card';
import { Eye, UserCheck, Loader2 } from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

const DEVICE_COLORS: Record<string, string> = {
  Desktop: '#3b82f6',
  Mobile: '#22c55e',
  Tablet: '#f97316',
};

const REFERRER_COLORS = ['#3b82f6', '#22c55e', '#a855f7', '#f97316', '#ef4444', '#eab308', '#ec4899', '#6366f1', '#14b8a6', '#f43f5e', '#6b7280'];

export function LandingPageAnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useLandingPageAnalytics(days);

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">Landing page performance and traffic sources</p>
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
          {/* Summary stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardContent className="p-6 flex items-center gap-4">
                <div className="rounded-lg bg-info/[.14] p-3">
                  <Eye className="h-6 w-6 text-brand" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Views</p>
                  <p className="text-3xl font-bold">{data.total_views.toLocaleString()}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6 flex items-center gap-4">
                <div className="rounded-lg bg-success/[.14] p-3">
                  <UserCheck className="h-6 w-6 text-success" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Unique Visitors</p>
                  <p className="text-3xl font-bold">{data.unique_views.toLocaleString()}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Views over time */}
          <ChartCard title="Views Over Time">
            <div className="h-[300px]">
              {data.views_over_time.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.views_over_time}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      className="text-xs"
                    />
                    <YAxis className="text-xs" />
                    <Tooltip labelFormatter={(v) => new Date(v).toLocaleDateString()} />
                    <Legend />
                    <Area type="monotone" dataKey="total" name="Total Views" stroke="#3b82f6" fill="#3b82f640" strokeWidth={2} />
                    <Area type="monotone" dataKey="unique" name="Unique Views" stroke="#22c55e" fill="#22c55e40" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-muted-foreground py-10">No view data</p>
              )}
            </div>
          </ChartCard>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top pages */}
            <ChartCard title="Top Pages">
              <div className="h-[300px]">
                {data.top_pages.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.top_pages} layout="vertical" margin={{ left: 120 }}>
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
                      <Bar dataKey="views" name="Views" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted-foreground py-10">No page data</p>
                )}
              </div>
            </ChartCard>

            {/* Device breakdown */}
            <ChartCard title="Device Breakdown">
              <div className="h-[300px]">
                {data.device_breakdown.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.device_breakdown}
                        dataKey="count"
                        nameKey="device"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        label={({ device, count }: any) => `${device}: ${count}`}
                      >
                        {data.device_breakdown.map((entry) => (
                          <Cell key={entry.device} fill={DEVICE_COLORS[entry.device] || '#6b7280'} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted-foreground py-10">No device data</p>
                )}
              </div>
            </ChartCard>
          </div>

          {/* Referrer breakdown */}
          <ChartCard title="Top Referrers">
            <div className="h-[300px]">
              {data.referrer_breakdown.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.referrer_breakdown} layout="vertical" margin={{ left: 140 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis type="number" className="text-xs" />
                    <YAxis
                      dataKey="source"
                      type="category"
                      width={130}
                      className="text-xs"
                      tickFormatter={(v) => v.length > 22 ? v.slice(0, 22) + '...' : v}
                    />
                    <Tooltip />
                    <Bar dataKey="count" name="Visits" radius={[0, 4, 4, 0]}>
                      {data.referrer_breakdown.map((_, i) => (
                        <Cell key={i} fill={REFERRER_COLORS[i % REFERRER_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-muted-foreground py-10">No referrer data</p>
              )}
            </div>
          </ChartCard>
        </div>
      ) : null}
    </div>
  );
}
