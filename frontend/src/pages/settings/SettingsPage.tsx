import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Users, Building2, Activity, TrendingUp, Mail, Sparkles } from 'lucide-react';
import { TeamTab } from './TeamTab';
import { OrganizationTab } from './OrganizationTab';
import { ActivityTab } from './ActivityTab';
import { LeadScoringTab } from './LeadScoringTab';
import { EmailTab } from './EmailTab';
import { AITab } from './AITab';
import { usePermissions } from '@/hooks/usePermissions';

export function SettingsPage() {
  const { canManageTeam, isProfessionalOrAbove } = usePermissions();
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
          <TabsTrigger value="email" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Email
          </TabsTrigger>
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
        <TabsContent value="email" className="mt-6">
          <EmailTab />
        </TabsContent>
        <TabsContent value="ai" className="mt-6">
          <AITab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
