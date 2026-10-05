import { useState, useEffect } from 'react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useForms } from '@/hooks/useForms';
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
    form_id: landingPage.form || null,
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
      form_id: landingPage.form || null,
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
                <span className="text-sm text-muted-foreground">/p/</span>
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

            <div className="space-y-2">
              <Label htmlFor="form">Embedded Form</Label>
              <Select
                value={formData.form_id || 'none'}
                onValueChange={(value) =>
                  setFormData({
                    ...formData,
                    form_id: value === 'none' ? null : value,
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a form..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No form</SelectItem>
                  {forms.map((form) => (
                    <SelectItem key={form.id} value={form.id}>
                      {form.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Select a form to embed in this landing page
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
