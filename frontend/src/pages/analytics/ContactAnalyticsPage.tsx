import { useState } from 'react';
import { useContactAnalytics } from '@/hooks/useAnalytics';
import { AnalyticsTabNav } from './AnalyticsOverviewPage';
import { StatCard } from '@/components/analytics/StatCard';
import { DateRangeSelector } from '@/components/analytics/DateRangeSelector';
import { ChartCard } from '@/components/analytics/ChartCard';
import { Users, UserPlus, UserMinus, Loader2 } from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

const ENGAGEMENT_COLORS: Record<string, string> = {
  high: '#22c55e',
  medium: '#3b82f6',
  low: '#f97316',
  none: '#6b7280',
};

const SOURCE_COLORS = ['#3b82f6', '#22c55e', '#a855f7', '#f97316', '#ef4444'];

const SUBSCRIPTION_COLORS = ['#22c55e', '#ef4444', '#f97316'];

export function ContactAnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useContactAnalytics(days);

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">Contact growth and engagement insights</p>
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-4 rounded-lg border p-6">
              <div className="rounded-lg bg-info/[.14] p-3">
                <Users className="h-6 w-6 text-brand" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Contacts</p>
                <p className="text-3xl font-bold">{data.total.toLocaleString()}</p>
              </div>
            </div>
            <StatCard
              title="New Contacts"
              trend={data.new_contacts}
              icon={UserPlus}
              color="green"
            />
            <StatCard
              title="Unsubscribes"
              trend={data.unsubscribes}
              icon={UserMinus}
              color="orange"
            />
          </div>

          {/* Growth chart */}
          <ChartCard title="Contact Growth">
            <div className="h-[300px]">
              {data.growth.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.growth}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      className="text-xs"
                    />
                    <YAxis className="text-xs" />
                    <Tooltip labelFormatter={(v) => new Date(v).toLocaleDateString()} />
                    <Area type="monotone" dataKey="count" name="New Contacts" stroke="#22c55e" fill="#22c55e40" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-muted-foreground py-10">No growth data</p>
              )}
            </div>
          </ChartCard>

          {/* 2x2 grid of distributions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Engagement distribution */}
            <ChartCard title="Engagement Distribution">
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.engagement_distribution}
                      dataKey="count"
                      nameKey="level"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label={({ level, count }: any) => `${level}: ${count}`}
                    >
                      {data.engagement_distribution.map((entry) => (
                        <Cell key={entry.level} fill={ENGAGEMENT_COLORS[entry.level] || '#6b7280'} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Source distribution */}
            <ChartCard title="Contact Sources">
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.source_distribution} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis type="number" className="text-xs" />
                    <YAxis dataKey="source" type="category" className="text-xs" width={75} />
                    <Tooltip />
                    <Bar dataKey="count" name="Contacts" radius={[0, 4, 4, 0]}>
                      {data.source_distribution.map((_, i) => (
                        <Cell key={i} fill={SOURCE_COLORS[i % SOURCE_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Subscription overview */}
            <ChartCard title="Subscription Status">
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Subscribed', value: data.subscription_overview.subscribed },
                        { name: 'Unsubscribed', value: data.subscription_overview.unsubscribed },
                        { name: 'Bounced', value: data.subscription_overview.bounced },
                      ]}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label={({ name, value }: any) => `${name}: ${value}`}
                    >
                      {SUBSCRIPTION_COLORS.map((color, i) => (
                        <Cell key={i} fill={color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Lead score histogram */}
            <ChartCard title="Lead Score Distribution">
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.lead_score_distribution}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="bucket" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip />
                    <Bar dataKey="count" name="Contacts" fill="#a855f7" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* New vs Unsubscribes */}
          <ChartCard title="New Contacts vs Unsubscribes">
            <div className="h-[300px]">
              {data.new_vs_unsubscribes.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.new_vs_unsubscribes}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      className="text-xs"
                    />
                    <YAxis className="text-xs" />
                    <Tooltip labelFormatter={(v) => new Date(v).toLocaleDateString()} />
                    <Legend />
                    <Line type="monotone" dataKey="new_contacts" name="New Contacts" stroke="#22c55e" strokeWidth={2} />
                    <Line type="monotone" dataKey="unsubscribes" name="Unsubscribes" stroke="#ef4444" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-muted-foreground py-10">No data for this period</p>
              )}
            </div>
          </ChartCard>
        </div>
      ) : null}
    </div>
  );
}
