import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { BarChart3, Share2 } from 'lucide-react';
import { AnalyticsTab } from './AnalyticsTab';
import { SocialTab } from './SocialTab';

export function IntegrationsPage() {
  const [activeTab, setActiveTab] = useState('analytics');

  return (
    <div className="w-full space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
        <p className="text-muted-foreground">
          Connect your analytics and social media platforms.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Analytics
          </TabsTrigger>
          <TabsTrigger value="social" className="flex items-center gap-2">
            <Share2 className="h-4 w-4" />
            Social Media
          </TabsTrigger>
        </TabsList>

        <TabsContent value="analytics" className="mt-6">
          <AnalyticsTab />
        </TabsContent>
        <TabsContent value="social" className="mt-6">
          <SocialTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
