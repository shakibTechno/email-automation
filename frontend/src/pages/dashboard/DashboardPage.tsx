import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDashboard } from '@/hooks/useDashboard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Users,
  Mail,
  FileText,
  Layout,
  TrendingUp,
  Eye,
  MousePointer,
  Send,
  Plus,
  ArrowRight,
  RefreshCw,
  Clock,
} from 'lucide-react';
import { format, parseISO } from 'date-fns';

// Stat Card Component
const StatCard = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = 'blue',
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  trend?: { value: number; label: string };
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'pink';
}) => {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
    pink: 'bg-pink-100 text-pink-600',
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-2">{value}</p>
            {subtitle && (
              <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
            )}
            {trend && (
              <p className={`text-sm mt-2 flex items-center gap-1 ${trend.value >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                <TrendingUp className={`h-4 w-4 ${trend.value < 0 ? 'rotate-180' : ''}`} />
                {trend.value >= 0 ? '+' : ''}{trend.value}% {trend.label}
              </p>
            )}
          </div>
          <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Simple Area Chart using CSS
const MiniChart = ({ data, height = 60 }: { data: number[]; height?: number }) => {
  if (!data || data.length === 0) return null;

  const max = Math.max(...data, 1);
  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * 100;
    const y = 100 - (value / max) * 100;
    return `${x},${y}`;
  }).join(' ');

  const areaPoints = `0,100 ${points} 100,100`;

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full" style={{ height }}>
      <defs>
        <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="rgb(59, 130, 246)" stopOpacity="0.3" />
          <stop offset="100%" stopColor="rgb(59, 130, 246)" stopOpacity="0.05" />
        </linearGradient>
      </defs>
      <polygon
        fill="url(#chartGradient)"
        points={areaPoints}
      />
      <polyline
        fill="none"
        stroke="rgb(59, 130, 246)"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
        points={points}
      />
    </svg>
  );
};

// Campaign Status Badge
const StatusBadge = ({ status }: { status: string }) => {
  const statusClasses: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    scheduled: 'bg-blue-100 text-blue-700',
    sending: 'bg-yellow-100 text-yellow-700',
    sent: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusClasses[status] || statusClasses.draft}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

export const DashboardPage = () => {
  const navigate = useNavigate();
  const [days, setDays] = useState(30);
  const { data, isLoading, refetch } = useDashboard(days);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  const overview = data?.overview;
  const campaignStats = data?.campaign_stats;
  const formStats = data?.form_stats;
  const landingPageStats = data?.landing_page_stats;
  const contactGrowth = data?.contact_growth || [];
  const recentCampaigns = data?.recent_campaigns || [];
  const recentSubmissions = data?.recent_submissions || [];
  const topLandingPages = data?.top_landing_pages || [];

  // Prepare chart data
  const contactChartData = contactGrowth.map(d => d.count);
  const submissionChartData = formStats?.submissions_by_day?.map(d => d.count) || [];
  const pageViewChartData = landingPageStats?.views_by_day?.map(d => d.views) || [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Welcome back! Here's what's happening.</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Button
          className="h-auto py-4 flex flex-col items-center gap-2"
          onClick={() => navigate('/campaigns/new')}
        >
          <Send className="h-5 w-5" />
          <span>New Campaign</span>
        </Button>
        <Button
          variant="outline"
          className="h-auto py-4 flex flex-col items-center gap-2"
          onClick={() => navigate('/contacts/new')}
        >
          <Users className="h-5 w-5" />
          <span>Add Contact</span>
        </Button>
        <Button
          variant="outline"
          className="h-auto py-4 flex flex-col items-center gap-2"
          onClick={() => navigate('/forms/new')}
        >
          <FileText className="h-5 w-5" />
          <span>Create Form</span>
        </Button>
        <Button
          variant="outline"
          className="h-auto py-4 flex flex-col items-center gap-2"
          onClick={() => navigate('/landing-pages')}
        >
          <Layout className="h-5 w-5" />
          <span>Landing Page</span>
        </Button>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Contacts"
          value={overview?.contacts.total.toLocaleString() || '0'}
          icon={Users}
          color="blue"
        />
        <StatCard
          title="Campaigns Sent"
          value={overview?.campaigns.sent || 0}
          subtitle={`${overview?.campaigns.total || 0} total campaigns`}
          icon={Mail}
          color="green"
        />
        <StatCard
          title="Active Forms"
          value={overview?.forms.active || 0}
          subtitle={`${overview?.forms.total || 0} total forms`}
          icon={FileText}
          color="purple"
        />
        <StatCard
          title="Published Pages"
          value={overview?.landing_pages.published || 0}
          subtitle={`${overview?.landing_pages.total || 0} total pages`}
          icon={Layout}
          color="orange"
        />
      </div>

      {/* Email Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Email Performance</CardTitle>
            <CardDescription>Campaign metrics for the last {days} days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <Send className="h-6 w-6 mx-auto mb-2 text-blue-600" />
                <p className="text-2xl font-bold">{campaignStats?.emails_sent.toLocaleString() || 0}</p>
                <p className="text-sm text-muted-foreground">Emails Sent</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <Mail className="h-6 w-6 mx-auto mb-2 text-green-600" />
                <p className="text-2xl font-bold">{campaignStats?.emails_delivered.toLocaleString() || 0}</p>
                <p className="text-sm text-muted-foreground">Delivered</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <Eye className="h-6 w-6 mx-auto mb-2 text-purple-600" />
                <p className="text-2xl font-bold">{campaignStats?.open_rate || 0}%</p>
                <p className="text-sm text-muted-foreground">Open Rate</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <MousePointer className="h-6 w-6 mx-auto mb-2 text-orange-600" />
                <p className="text-2xl font-bold">{campaignStats?.click_rate || 0}%</p>
                <p className="text-sm text-muted-foreground">Click Rate</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Contact Growth</CardTitle>
            <CardDescription>New contacts over time</CardDescription>
          </CardHeader>
          <CardContent>
            {contactChartData.length > 0 ? (
              <MiniChart data={contactChartData} height={100} />
            ) : (
              <div className="h-[100px] flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            )}
            <p className="text-center text-sm text-muted-foreground mt-2">
              {contactGrowth.reduce((sum, d) => sum + d.count, 0)} new contacts in {days} days
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Forms & Landing Pages */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Form Submissions</CardTitle>
              <CardDescription>Last {days} days</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/forms')}>
              View All <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-3xl font-bold">{formStats?.total_submissions || 0}</p>
                <p className="text-sm text-muted-foreground">Total submissions</p>
              </div>
              {submissionChartData.length > 0 && (
                <div className="w-32">
                  <MiniChart data={submissionChartData} height={40} />
                </div>
              )}
            </div>
            {recentSubmissions.length > 0 ? (
              <div className="space-y-3">
                {recentSubmissions.slice(0, 3).map((submission) => (
                  <div key={submission.id} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div>
                      <p className="font-medium text-sm">{submission.form_name}</p>
                      <p className="text-xs text-muted-foreground">{submission.contact_email || 'Anonymous'}</p>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {format(parseISO(submission.created_at), 'MMM d, h:mm a')}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">No recent submissions</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Landing Page Views</CardTitle>
              <CardDescription>Last {days} days</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/landing-pages')}>
              View All <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-3xl font-bold">{landingPageStats?.total_views || 0}</p>
                <p className="text-sm text-muted-foreground">{landingPageStats?.unique_views || 0} unique visitors</p>
              </div>
              {pageViewChartData.length > 0 && (
                <div className="w-32">
                  <MiniChart data={pageViewChartData} height={40} />
                </div>
              )}
            </div>
            {topLandingPages.length > 0 ? (
              <div className="space-y-3">
                {topLandingPages.slice(0, 3).map((page) => (
                  <div key={page.id} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div>
                      <p className="font-medium text-sm">{page.name}</p>
                      <p className="text-xs text-muted-foreground">/{page.slug}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">{page.view_count} views</p>
                      <p className="text-xs text-muted-foreground">{page.conversion_count} conversions</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">No published pages yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Campaigns */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Campaigns</CardTitle>
            <CardDescription>Your latest email campaigns</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={() => navigate('/campaigns')}>
            View All <ArrowRight className="h-4 w-4 ml-1" />
          </Button>
        </CardHeader>
        <CardContent>
          {recentCampaigns.length > 0 ? (
            <div className="space-y-4">
              {recentCampaigns.map((campaign) => (
                <div
                  key={campaign.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                  onClick={() => navigate(`/campaigns/${campaign.id}`)}
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                      <Mail className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium">{campaign.name}</p>
                      <p className="text-sm text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {campaign.sent_at
                          ? `Sent ${format(parseISO(campaign.sent_at), 'MMM d, yyyy')}`
                          : `Created ${format(parseISO(campaign.created_at), 'MMM d, yyyy')}`
                        }
                      </p>
                    </div>
                  </div>
                  <StatusBadge status={campaign.status} />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Mail className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">No campaigns yet</p>
              <Button onClick={() => navigate('/campaigns/new')}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Campaign
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DashboardPage;
