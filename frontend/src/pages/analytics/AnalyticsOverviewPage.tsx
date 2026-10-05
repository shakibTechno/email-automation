import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAnalyticsOverview } from '@/hooks/useAnalytics';
import { StatCard } from '@/components/analytics/StatCard';
import { DateRangeSelector } from '@/components/analytics/DateRangeSelector';
import { ChartCard } from '@/components/analytics/ChartCard';
import { Mail, Users, FileText, Eye, Loader2 } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

const NAV_TABS = [
  { label: 'Overview', path: '/analytics' },
  { label: 'Campaigns', path: '/analytics/campaigns' },
  { label: 'Contacts', path: '/analytics/contacts' },
  { label: 'Forms', path: '/analytics/forms' },
  { label: 'Landing Pages', path: '/analytics/landing-pages' },
];

export function AnalyticsTabNav() {
  const location = useLocation();

  return (
    <nav className="flex gap-1 border-b mb-6">
      {NAV_TABS.map((tab) => {
        const isActive = location.pathname === tab.path;
        return (
          <Link
            key={tab.path}
            to={tab.path}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/50'
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AnalyticsOverviewPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useAnalyticsOverview(days);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">
            Track your marketing performance across all channels
          </p>
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Emails Sent"
              trend={data.overview.emails_sent}
              icon={Mail}
              color="blue"
            />
            <StatCard
              title="New Contacts"
              trend={data.overview.new_contacts}
              icon={Users}
              color="green"
            />
            <StatCard
              title="Form Submissions"
              trend={data.overview.form_submissions}
              icon={FileText}
              color="purple"
            />
            <StatCard
              title="Page Views"
              trend={data.overview.page_views}
              icon={Eye}
              color="orange"
            />
          </div>

          <ChartCard title="Performance Trends">
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.trends}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    className="text-xs"
                  />
                  <YAxis className="text-xs" />
                  <Tooltip
                    labelFormatter={(v) => new Date(v).toLocaleDateString()}
                    contentStyle={{ borderRadius: '8px', fontSize: '13px' }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="emails_sent"
                    name="Emails Sent"
                    stroke="#3b82f6"
                    fill="#3b82f680"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="new_contacts"
                    name="New Contacts"
                    stroke="#22c55e"
                    fill="#22c55e80"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="form_submissions"
                    name="Submissions"
                    stroke="#a855f7"
                    fill="#a855f780"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="page_views"
                    name="Page Views"
                    stroke="#f97316"
                    fill="#f9731680"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </div>
      ) : (
        <p className="text-center text-muted-foreground py-10">No data available</p>
      )}
    </div>
  );
}
