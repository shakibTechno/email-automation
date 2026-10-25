import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Users, Building2, Activity, TrendingUp, Mail, Sparkles, Globe, ListPlus,
} from 'lucide-react';
import { TeamTab } from './TeamTab';
import { OrganizationTab } from './OrganizationTab';
import { ActivityTab } from './ActivityTab';
import { LeadScoringTab } from './LeadScoringTab';
import { EmailTab } from './EmailTab';
import { DomainsTab } from './DomainsTab';
import { CustomFieldsTab } from './CustomFieldsTab';
import { AITab } from './AITab';
import { usePermissions } from '@/hooks/usePermissions';

export function SettingsPage() {
  const { canManageTeam, isProfessionalOrAbove, planAtLeast } = usePermissions();
  // Mirrors CUSTOM_DOMAIN_MIN_PLAN on the server. The API refuses lower
  // tiers regardless; hiding the tab just avoids offering what it will deny.
  const canUseCustomDomains = planAtLeast('starter');
  const [activeTab, setActiveTab] = useState('team');

  return (
    <div className="w-full space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your team, organization, and account settings.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="team" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Team
          </TabsTrigger>
          <TabsTrigger value="organization" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Organization
          </TabsTrigger>
          {canManageTeam && (
            <TabsTrigger value="activity" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Activity
            </TabsTrigger>
          )}
          {isProfessionalOrAbove && (
            <TabsTrigger value="lead-scoring" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Lead Scoring
            </TabsTrigger>
          )}
          <TabsTrigger value="custom-fields" className="flex items-center gap-2">
            <ListPlus className="h-4 w-4" />
            Custom Fields
          </TabsTrigger>
          <TabsTrigger value="email" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Email
          </TabsTrigger>
          {canUseCustomDomains && (
            <TabsTrigger value="domains" className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              Domains
            </TabsTrigger>
          )}
          <TabsTrigger value="ai" className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            AI
          </TabsTrigger>
        </TabsList>

        <TabsContent value="team" className="mt-6">
          <TeamTab />
        </TabsContent>
        <TabsContent value="organization" className="mt-6">
          <OrganizationTab />
        </TabsContent>
        {canManageTeam && (
          <TabsContent value="activity" className="mt-6">
            <ActivityTab />
          </TabsContent>
        )}
        {isProfessionalOrAbove && (
          <TabsContent value="lead-scoring" className="mt-6">
            <LeadScoringTab />
          </TabsContent>
        )}
        <TabsContent value="custom-fields" className="mt-6">
          <CustomFieldsTab />
        </TabsContent>
        <TabsContent value="email" className="mt-6">
          <EmailTab />
        </TabsContent>
        {canUseCustomDomains && (
          <TabsContent value="domains" className="mt-6">
            <DomainsTab />
          </TabsContent>
        )}
        <TabsContent value="ai" className="mt-6">
          <AITab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
