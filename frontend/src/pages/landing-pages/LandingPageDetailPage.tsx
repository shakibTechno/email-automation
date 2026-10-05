import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LandingPageStatusBadge } from '@/components/landing-pages/LandingPageStatusBadge';
import {
  useLandingPage,
  usePublishLandingPage,
  useUnpublishLandingPage,
} from '@/hooks/useLandingPages';
import { useLandingPageAnalytics } from '@/hooks/useLandingPageAnalytics';
import {
  ArrowLeft,
  Edit,
  ExternalLink,
  Globe,
  CircleSlash,
  Eye,
  Users,
  TrendingUp,
  Calendar,
  Copy,
  Check,
} from 'lucide-react';

export const LandingPageDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);
  const [days, setDays] = useState(30);

  const { landingPage, isLoading } = useLandingPage(id || '');
  const { analytics, isLoading: analyticsLoading } = useLandingPageAnalytics(
    id || '',
    days
  );
  const publishMutation = usePublishLandingPage();
  const unpublishMutation = useUnpublishLandingPage();

  const copyUrl = () => {
    if (landingPage?.public_url) {
      navigator.clipboard.writeText(landingPage.public_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!landingPage) {
    return (
      <div className="w-full">
        <p>Landing page not found</p>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/landing-pages')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold">{landingPage.name}</h1>
              <LandingPageStatusBadge status={landingPage.status} />
            </div>
            <p className="text-muted-foreground text-sm">
              Created {formatDate(landingPage.created_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {landingPage.status === 'published' && (
            <Button
              variant="outline"
              onClick={() => window.open(landingPage.public_url, '_blank')}
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              View Live
            </Button>
          )}
          {landingPage.status === 'draft' ? (
            <Button
              variant="outline"
              onClick={() => publishMutation.mutate(landingPage.id)}
              disabled={publishMutation.isPending}
            >
              <Globe className="h-4 w-4 mr-2" />
              Publish
            </Button>
          ) : (
            <Button
              variant="outline"
              onClick={() => unpublishMutation.mutate(landingPage.id)}
              disabled={unpublishMutation.isPending}
            >
              <CircleSlash className="h-4 w-4 mr-2" />
              Unpublish
            </Button>
          )}
          <Button onClick={() => navigate(`/landing-pages/${id}/edit`)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Page
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6 mt-6">
          <div className="grid grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Views
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Eye className="h-5 w-5 text-muted-foreground" />
                  <span className="text-2xl font-bold">
                    {landingPage.view_count.toLocaleString()}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Conversions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-muted-foreground" />
                  <span className="text-2xl font-bold">
                    {landingPage.conversion_count.toLocaleString()}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Conversion Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-muted-foreground" />
                  <span className="text-2xl font-bold">
                    {landingPage.conversion_rate}%
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Published
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm">
                    {landingPage.published_at
                      ? new Date(landingPage.published_at).toLocaleDateString()
                      : 'Not published'}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Page Details */}
            <Card>
              <CardHeader>
                <CardTitle>Page Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    URL
                  </label>
                  <div className="flex items-center gap-2 mt-1">
                    <code className="flex-1 text-sm bg-muted px-3 py-2 rounded">
                      {landingPage.public_url}
                    </code>
                    <Button variant="outline" size="icon" onClick={copyUrl}>
                      {copied ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Slug
                  </label>
                  <p className="mt-1">/p/{landingPage.slug}</p>
                </div>

                {landingPage.form_name && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Embedded Form
                    </label>
                    <p className="mt-1">{landingPage.form_name}</p>
                  </div>
                )}

                {landingPage.created_by_name && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Created By
                    </label>
                    <p className="mt-1">{landingPage.created_by_name}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* SEO Settings */}
            <Card>
              <CardHeader>
                <CardTitle>SEO Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Page Title
                  </label>
                  <p className="mt-1">
                    {landingPage.seo_title || landingPage.name}
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Meta Description
                  </label>
                  <p className="mt-1 text-sm">
                    {landingPage.seo_description || 'Not set'}
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Keywords
                  </label>
                  <p className="mt-1 text-sm">
                    {landingPage.seo_keywords || 'Not set'}
                  </p>
                </div>

                {(landingPage.google_analytics_id ||
                  landingPage.facebook_pixel_id) && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Tracking
                    </label>
                    <div className="mt-1 flex gap-2">
                      {landingPage.google_analytics_id && (
                        <span className="text-xs bg-muted px-2 py-1 rounded">
                          Google Analytics
                        </span>
                      )}
                      {landingPage.facebook_pixel_id && (
                        <span className="text-xs bg-muted px-2 py-1 rounded">
                          Facebook Pixel
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-6 mt-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Page Analytics</h2>
            <div className="flex items-center gap-2">
              {[7, 30, 90].map((d) => (
                <Button
                  key={d}
                  variant={days === d ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setDays(d)}
                >
                  {d} days
                </Button>
              ))}
            </div>
          </div>

          {analyticsLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : analytics ? (
            <>
              <div className="grid grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Total Views
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <span className="text-2xl font-bold">
                      {analytics.total_views.toLocaleString()}
                    </span>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Unique Views
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <span className="text-2xl font-bold">
                      {analytics.unique_views.toLocaleString()}
                    </span>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Conversions
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <span className="text-2xl font-bold">
                      {analytics.conversion_count.toLocaleString()}
                    </span>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Conversion Rate
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <span className="text-2xl font-bold">
                      {analytics.conversion_rate}%
                    </span>
                  </CardContent>
                </Card>
              </div>

              {/* Views by Date Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Daily Views</CardTitle>
                </CardHeader>
                <CardContent>
                  {analytics.views_by_date.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">
                      No data for this period
                    </p>
                  ) : (
                    <div className="max-h-96 overflow-y-auto">
                      <table className="w-full">
                        <thead className="sticky top-0 bg-background">
                          <tr className="border-b">
                            <th className="text-left py-2 font-medium">Date</th>
                            <th className="text-right py-2 font-medium">
                              Views
                            </th>
                            <th className="text-right py-2 font-medium">
                              Unique
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {analytics.views_by_date.map((row) => (
                            <tr key={row.date} className="border-b">
                              <td className="py-2">
                                {new Date(row.date).toLocaleDateString()}
                              </td>
                              <td className="text-right py-2">{row.views}</td>
                              <td className="text-right py-2">
                                {row.unique_views}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No analytics data available
            </p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};
