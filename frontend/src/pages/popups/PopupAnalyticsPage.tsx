import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, Eye, MousePointerClick, Pencil, Users, X,
} from 'lucide-react';
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis,
  YAxis,
} from 'recharts';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { ChartCard } from '@/components/analytics/ChartCard';
import { PopupStatusBadge } from '@/components/popups/PopupStatusBadge';
import { usePopup, usePopupAnalytics } from '@/hooks/usePopups';
import { popupTypeLabels } from '@/types/popup';

const RANGES = [7, 30, 90] as const;

const Stat = ({
  label, value, hint, icon: Icon,
}: {
  label: string;
  value: string;
  hint?: string;
  icon: React.ElementType;
}) => (
  <Card>
    <CardContent className="flex items-start justify-between p-4">
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold">{value}</p>
        {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
      </div>
      <span className="rounded-md bg-muted p-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
      </span>
    </CardContent>
  </Card>
);

export const PopupAnalyticsPage = () => {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [days, setDays] = useState<number>(30);

  const { popup, isLoading: popupLoading } = usePopup(id);
  const { analytics, isLoading } = usePopupAnalytics(id, days);

  if (popupLoading) {
    return <p className="p-6 text-sm text-muted-foreground">Loading&hellip;</p>;
  }
  if (!popup) {
    return <p className="p-6 text-sm text-muted-foreground">That pop-up no longer exists.</p>;
  }

  const stats = analytics;
  const chart = (stats?.over_time || []).map((row) => ({
    ...row,
    label: new Date(row.date).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric',
    }),
  }));
  const hasAnything = (stats?.impressions || 0) > 0;

  return (
    <div className="w-full space-y-3.5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/popups')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold">{popup.name}</h1>
              <PopupStatusBadge status={popup.status} isLive={popup.is_live} />
            </div>
            <p className="text-sm text-muted-foreground">
              {popupTypeLabels[popup.popup_type]}
              {popup.form_name ? ` · captures with ${popup.form_name}` : ' · no form'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
            <SelectTrigger className="w-[150px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              {RANGES.map((range) => (
                <SelectItem key={range} value={String(range)}>
                  Last {range} days
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={() => navigate(`/popups/${id}/edit`)}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Button>
        </div>
      </div>

      {isLoading && !stats ? (
        <p className="text-sm text-muted-foreground">Loading the numbers&hellip;</p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Impressions"
              value={(stats?.impressions || 0).toLocaleString()}
              hint={`${(stats?.unique_views || 0).toLocaleString()} people`}
              icon={Eye}
            />
            <Stat
              label="Clicks"
              value={(stats?.clicks || 0).toLocaleString()}
              icon={MousePointerClick}
            />
            <Stat
              label="Conversions"
              value={(stats?.conversions || 0).toLocaleString()}
              hint={popup.form_name ? 'Form submissions' : 'CTA clicks'}
              icon={Users}
            />
            <Stat
              label="Dismissed"
              value={(stats?.dismissals || 0).toLocaleString()}
              hint={`${stats?.dismiss_rate || 0}% of impressions`}
              icon={X}
            />
          </div>

          {/* A rate without its sample size invites reading 100% off two
              impressions as a result. */}
          <Card>
            <CardContent className="flex flex-wrap items-baseline gap-x-3 gap-y-1 p-4">
              <span className="text-3xl font-semibold">
                {stats?.conversion_rate ?? 0}%
              </span>
              <span className="text-sm text-muted-foreground">
                conversion rate &mdash; {(stats?.conversions || 0).toLocaleString()} of{' '}
                {(stats?.impressions || 0).toLocaleString()} impressions
              </span>
              {(stats?.impressions || 0) < 100 && hasAnything && (
                <span className="text-xs text-warning">
                  Too few impressions to read much into yet.
                </span>
              )}
            </CardContent>
          </Card>

          <ChartCard title="Impressions and clicks">
            {hasAnything ? (
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chart}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="impressions" name="Impressions" fill="#3b82f6" />
                    <Bar dataKey="clicks" name="Clicks" fill="#22c55e" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="py-10 text-center text-sm text-muted-foreground">
                <p>Nothing recorded yet.</p>
                <p className="mt-1">
                  {popup.status === 'published'
                    ? 'Impressions appear once a visitor sees it. The tracking snippet has to be installed on your site.'
                    : 'Publish it and install the tracking snippet to start measuring.'}
                </p>
                <Button
                  variant="link" className="mt-1"
                  onClick={() => navigate('/settings?tab=tracking')}
                >
                  Tracking snippet
                </Button>
              </div>
            )}
          </ChartCard>

          <p className="text-xs text-muted-foreground">
            Lifetime totals on the list page can run ahead of these: old events
            are pruned, and a counter that fell when they aged out would be
            worse than one that disagrees.
          </p>
        </>
      )}
    </div>
  );
};
