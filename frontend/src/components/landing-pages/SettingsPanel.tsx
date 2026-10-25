import { useState, useEffect, useMemo } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ClipboardList } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useForms } from '@/hooks/useForms';
import { useLandingDomains } from '@/hooks/useLandingDomains';
import type { LandingPage, UpdateLandingPageData } from '@/types/landing-page';

interface SettingsPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  landingPage: LandingPage;
  onSave: (data: UpdateLandingPageData) => void;
  isSaving?: boolean;
}

export const SettingsPanel = ({
  open,
  onOpenChange,
  landingPage,
  onSave,
  isSaving,
}: SettingsPanelProps) => {
  const { forms } = useForms({ status: 'active' });
  const { domains } = useLandingDomains(open);
  // Only verified domains are offered: an unverified one serves nothing, so
  // pinning a page to it would take the page's address offline.
  const liveDomains = domains.filter((d) => d.is_verified);
  const primaryDomain = liveDomains.find((d) => d.is_primary);
  const pinnedDomain = liveDomains.find((d) => d.id === landingPage.domain);
  const servingDomain = pinnedDomain ?? (landingPage.domain ? undefined : primaryDomain);
  const servingBase = servingDomain ? `${servingDomain.domain}/` : '/p/';

  // The builder stamps each embed it inserts with `data-form-id`, so the saved
  // markup is the source of truth for what this page actually captures to.
  const embeddedForms = useMemo(() => {
    const html = landingPage.html_content || '';
    const ids = new Set(
      Array.from(html.matchAll(/data-form-id=["']([^"']+)["']/g), (m) => m[1])
    );
    return Array.from(ids).map((id) => ({
      id,
      name: forms.find((f) => f.id === id)?.name ?? 'Untitled form',
    }));
  }, [landingPage.html_content, forms]);

  const [formData, setFormData] = useState<UpdateLandingPageData>({
    name: landingPage.name,
    slug: landingPage.slug,
    seo_title: landingPage.seo_title || '',
    seo_description: landingPage.seo_description || '',
    seo_keywords: landingPage.seo_keywords || '',
    google_analytics_id: landingPage.google_analytics_id || '',
    facebook_pixel_id: landingPage.facebook_pixel_id || '',
    custom_head_code: landingPage.custom_head_code || '',
    custom_body_code: landingPage.custom_body_code || '',
    domain: landingPage.domain ?? null,
    is_domain_home: landingPage.is_domain_home ?? false,
  });

  useEffect(() => {
    setFormData({
      name: landingPage.name,
      slug: landingPage.slug,
      seo_title: landingPage.seo_title || '',
      seo_description: landingPage.seo_description || '',
      seo_keywords: landingPage.seo_keywords || '',
      google_analytics_id: landingPage.google_analytics_id || '',
      facebook_pixel_id: landingPage.facebook_pixel_id || '',
      custom_head_code: landingPage.custom_head_code || '',
      custom_body_code: landingPage.custom_body_code || '',
      domain: landingPage.domain ?? null,
      is_domain_home: landingPage.is_domain_home ?? false,
      });
  }, [landingPage]);

  const handleSave = () => {
    onSave(formData);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Page Settings</SheetTitle>
        </SheetHeader>

        <Tabs defaultValue="general" className="mt-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="seo">SEO</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="advanced">Advanced</TabsTrigger>
          </TabsList>

          {/* General Tab */}
          <TabsContent value="general" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="name">Page Name</Label>
              <Input
                id="name"
                value={formData.name || ''}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="slug">URL Slug</Label>
              <div className="flex items-center gap-2">
                {/* Shows the real prefix, which depends on where this page is
                    actually served from. It used to read "/p/" always, which
                    was wrong for a page on a connected domain. */}
                <span className="shrink-0 text-sm text-muted-foreground">
                  {servingBase}
                </span>
                <Input
                  id="slug"
                  value={formData.slug || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, slug: e.target.value })
                  }
                />
              </div>
              <p className="text-xs text-muted-foreground">
                The URL path for your landing page
              </p>
            </div>

            {liveDomains.length > 0 && (
              <div className="space-y-2">
                <Label htmlFor="page-domain">Served from</Label>
                <Select
                  value={formData.domain ?? 'primary'}
                  onValueChange={(value) =>
                    setFormData({
                      ...formData,
                      domain: value === 'primary' ? null : value,
                    })
                  }
                >
                  <SelectTrigger id="page-domain">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {/* Default rather than a fixed choice, so connecting or
                        changing the primary domain moves this page too. */}
                    <SelectItem value="primary">
                      {primaryDomain
                        ? `Default (${primaryDomain.domain})`
                        : 'Default domain'}
                    </SelectItem>
                    {liveDomains.map((domain) => (
                      <SelectItem key={domain.id} value={domain.id}>
                        {domain.domain}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Manage domains in Settings &rarr; Domains.
                </p>
              </div>
            )}

            {/* This used to be a form picker that wrote `form_id` to the page
                and was never read when rendering it — the published page only
                ever shows forms placed on the canvas. Two controls for one job,
                one of them inert, is the confusion. The canvas is the real
                mechanism, so this reports what it placed rather than offering a
                second way to set it. */}
            <div className="space-y-2">
              <Label>Embedded Forms</Label>
              {embeddedForms.length > 0 ? (
                <ul className="space-y-1">
                  {embeddedForms.map((form) => (
                    <li
                      key={form.id}
                      className="flex items-center gap-2 rounded-md border bg-secondary/40 px-3 py-2 text-[13px]"
                    >
                      <ClipboardList className="h-3.5 w-3.5 flex-none text-subtle-foreground" />
                      <span className="truncate">{form.name}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="rounded-md border border-dashed px-3 py-2.5 text-[12.5px] text-muted-foreground">
                  No form on this page yet. Add one from the{' '}
                  <span className="font-medium text-foreground">Forms</span> tab in the
                  left panel of the builder.
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Submissions from these forms count as conversions for this page.
              </p>
            </div>
          </TabsContent>

          {/* SEO Tab */}
          <TabsContent value="seo" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="seo_title">Page Title</Label>
              <Input
                id="seo_title"
                value={formData.seo_title || ''}
                onChange={(e) =>
                  setFormData({ ...formData, seo_title: e.target.value })
                }
                maxLength={70}
              />
              <p className="text-xs text-muted-foreground">
                {(formData.seo_title?.length || 0)}/70 characters
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="seo_description">Meta Description</Label>
              <Textarea
                id="seo_description"
                value={formData.seo_description || ''}
                onChange={(e) =>
                  setFormData({ ...formData, seo_description: e.target.value })
                }
                maxLength={160}
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                {(formData.seo_description?.length || 0)}/160 characters
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="seo_keywords">Meta Keywords</Label>
              <Input
                id="seo_keywords"
                value={formData.seo_keywords || ''}
                onChange={(e) =>
                  setFormData({ ...formData, seo_keywords: e.target.value })
                }
                placeholder="keyword1, keyword2, keyword3"
              />
            </div>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="google_analytics_id">Google Analytics ID</Label>
              <Input
                id="google_analytics_id"
                value={formData.google_analytics_id || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    google_analytics_id: e.target.value,
                  })
                }
                placeholder="G-XXXXXXXXXX"
              />
              <p className="text-xs text-muted-foreground">
                Your Google Analytics 4 measurement ID
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="facebook_pixel_id">Facebook Pixel ID</Label>
              <Input
                id="facebook_pixel_id"
                value={formData.facebook_pixel_id || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    facebook_pixel_id: e.target.value,
                  })
                }
                placeholder="123456789012345"
              />
              <p className="text-xs text-muted-foreground">
                Your Facebook Pixel ID for conversion tracking
              </p>
            </div>
          </TabsContent>

          {/* Advanced Tab */}
          <TabsContent value="advanced" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="custom_head_code">Custom Head Code</Label>
              <Textarea
                id="custom_head_code"
                value={formData.custom_head_code || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    custom_head_code: e.target.value,
                  })
                }
                placeholder="<script>...</script>"
                rows={4}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Code injected before the closing &lt;/head&gt; tag
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="custom_body_code">Custom Body Code</Label>
              <Textarea
                id="custom_body_code"
                value={formData.custom_body_code || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    custom_body_code: e.target.value,
                  })
                }
                placeholder="<script>...</script>"
                rows={4}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Code injected before the closing &lt;/body&gt; tag
              </p>
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end gap-2 mt-6 pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
};
