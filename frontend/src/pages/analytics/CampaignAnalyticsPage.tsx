import { useState } from 'react';
import { useCampaignAnalytics, useCampaignDetail, useExportCampaignReport } from '@/hooks/useAnalytics';
import { AnalyticsTabNav } from './AnalyticsOverviewPage';
import { DateRangeSelector } from '@/components/analytics/DateRangeSelector';
import { ChartCard } from '@/components/analytics/ChartCard';
import { CampaignComparisonDialog } from '@/components/analytics/CampaignComparisonDialog';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Send,
  MousePointer,
  Eye,
  AlertTriangle,
  Download,
  GitCompare,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react';
import { Fragment } from 'react';
import {
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
import type { CampaignMetrics } from '@/types/analytics';

const PIE_COLORS = ['#22c55e', '#3b82f6', '#a855f7', '#f97316', '#ef4444', '#6b7280', '#eab308', '#ec4899'];

function SummaryCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: React.ElementType }) {
  return (
    <Card>
      <CardContent className="p-4 flex items-center gap-3">
        <div className="rounded-lg bg-muted p-2">
          <Icon className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-xl font-bold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function CampaignDetailInline({ campaignId }: { campaignId: string }) {
  const { data, isLoading } = useCampaignDetail(campaignId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-muted/30 rounded-lg">
      <ChartCard title="Status Breakdown">
        <div className="h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data.status_breakdown}
                dataKey="count"
                nameKey="status"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={({ status, count }: any) => `${status}: ${count}`}
              >
                {data.status_breakdown.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <ChartCard title="Engagement Over Time">
        <div className="h-[220px]">
          {data.engagement_over_time.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.engagement_over_time}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  className="text-xs"
                />
                <YAxis className="text-xs" />
                <Tooltip labelFormatter={(v) => new Date(v).toLocaleDateString()} />
                <Legend />
                <Line type="monotone" dataKey="opens" name="Opens" stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="clicks" name="Clicks" stroke="#22c55e" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center text-muted-foreground py-10">No engagement data</p>
          )}
        </div>
      </ChartCard>
    </div>
  );
}

export function CampaignAnalyticsPage() {
  const [days, setDays] = useState(30);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [sortField, setSortField] = useState<keyof CampaignMetrics>('sent_at');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const { data, isLoading } = useCampaignAnalytics(days);
  const exportMutation = useExportCampaignReport();

  const handleSort = (field: keyof CampaignMetrics) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const sortedCampaigns = data?.campaigns
    ? [...data.campaigns].sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        if (aVal == null && bVal == null) return 0;
        if (aVal == null) return 1;
        if (bVal == null) return -1;
        if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
        return 0;
      })
    : [];

  const SortHeader = ({ field, label }: { field: keyof CampaignMetrics; label: string }) => (
    <th
      className="text-left py-3 px-3 font-medium text-sm cursor-pointer hover:text-foreground select-none"
      onClick={() => handleSort(field)}
    >
      <span className="flex items-center gap-1">
        {label}
        {sortField === field && (
          sortDir === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
        )}
      </span>
    </th>
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">Campaign performance metrics</p>
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
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <SummaryCard label="Total Sent" value={data.summary.total_sent.toLocaleString()} icon={Send} />
            <SummaryCard label="Avg Open Rate" value={`${data.summary.avg_open_rate}%`} icon={Eye} />
            <SummaryCard label="Avg Click Rate" value={`${data.summary.avg_click_rate}%`} icon={MousePointer} />
            <SummaryCard label="Total Bounced" value={data.summary.total_bounced.toLocaleString()} icon={AlertTriangle} />
          </div>

          {/* Top campaigns bar chart */}
          {data.top_campaigns.length > 0 && (
            <ChartCard title="Top 5 Campaigns by Open Rate">
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data.top_campaigns.slice(0, 5)}
                    layout="vertical"
                    margin={{ left: 120 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} className="text-xs" />
                    <YAxis
                      dataKey="name"
                      type="category"
                      width={110}
                      className="text-xs"
                      tickFormatter={(v) => v.length > 18 ? v.slice(0, 18) + '...' : v}
                    />
                    <Tooltip formatter={(v: any) => `${v}%`} />
                    <Bar dataKey="open_rate" name="Open Rate" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCompareOpen(true)}
              disabled={data.campaigns.length < 2}
            >
              <GitCompare className="h-4 w-4 mr-2" />
              Compare
            </Button>
          </div>

          {/* Campaigns table */}
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b text-muted-foreground">
                  <tr>
                    <SortHeader field="name" label="Campaign" />
                    <SortHeader field="sent_at" label="Sent" />
                    <SortHeader field="recipient_count" label="Recipients" />
                    <SortHeader field="open_rate" label="Open Rate" />
                    <SortHeader field="click_rate" label="Click Rate" />
                    <SortHeader field="bounce_rate" label="Bounce Rate" />
                    <th className="py-3 px-3 text-right font-medium text-sm">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {sortedCampaigns.map((c) => (
                    <Fragment key={c.id}>
                      <tr
                        className="hover:bg-muted/50 cursor-pointer"
                        onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                      >
                        <td className="py-3 px-3 font-medium">{c.name}</td>
                        <td className="py-3 px-3 text-muted-foreground">
                          {c.sent_at ? new Date(c.sent_at).toLocaleDateString() : '-'}
                        </td>
                        <td className="py-3 px-3">{c.recipient_count.toLocaleString()}</td>
                        <td className="py-3 px-3">
                          <Badge variant="secondary">{c.open_rate}%</Badge>
                        </td>
                        <td className="py-3 px-3">
                          <Badge variant="secondary">{c.click_rate}%</Badge>
                        </td>
                        <td className="py-3 px-3">
                          <Badge variant={c.bounce_rate > 5 ? 'destructive' : 'secondary'}>
                            {c.bounce_rate}%
                          </Badge>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              exportMutation.mutate({ id: c.id, name: c.name });
                            }}
                            disabled={exportMutation.isPending}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                      {expandedId === c.id && (
                        <tr>
                          <td colSpan={7} className="p-4">
                            <CampaignDetailInline campaignId={c.id} />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                  {sortedCampaigns.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-10 text-center text-muted-foreground">
                        No sent campaigns found in this period
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          <CampaignComparisonDialog
            open={compareOpen}
            onOpenChange={setCompareOpen}
            campaigns={data.campaigns}
          />
        </div>
      ) : null}
    </div>
  );
}
