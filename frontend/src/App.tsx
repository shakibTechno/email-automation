import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';

// Layouts
import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

// Auth Pages
import { LoginPage } from '@/pages/auth/LoginPage';
import { RegisterPage } from '@/pages/auth/RegisterPage';
import { ForgotPasswordPage } from '@/pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from '@/pages/auth/ResetPasswordPage';
import { VerifyEmailPage } from '@/pages/auth/VerifyEmailPage';

// Contact Pages
import { ContactListPage } from '@/pages/contacts/ContactListPage';
import { ContactCreatePage } from '@/pages/contacts/ContactCreatePage';
import { ContactEditPage } from '@/pages/contacts/ContactEditPage';
import { ContactDetailPage } from '@/pages/contacts/ContactDetailPage';
import { TagManagementPage } from '@/pages/contacts/TagManagementPage';

// Template Pages
import { TemplateListPage } from '@/pages/templates/TemplateListPage';
import { TemplateEditorPage } from '@/pages/templates/TemplateEditorPage';

// Campaign Pages
import { CampaignListPage } from '@/pages/campaigns/CampaignListPage';
import { CampaignWizardPage } from '@/pages/campaigns/CampaignWizardPage';
import { CampaignDetailPage } from '@/pages/campaigns/CampaignDetailPage';

// Form Pages
import { FormListPage } from '@/pages/forms/FormListPage';
import { FormBuilderPage } from '@/pages/forms/FormBuilderPage';
import {
  PopupListPage, PopupBuilderPage, PopupAnalyticsPage,
} from '@/pages/popups';
import { FormDetailPage } from '@/pages/forms/FormDetailPage';
import { PublicFormPage } from '@/pages/forms/PublicFormPage';

// Landing Page Pages
import {
  LandingPageListPage,
  LandingPageBuilderPage,
  LandingPageDetailPage,
  LandingPagePreviewPage,
} from '@/pages/landing-pages';

// Workflow Pages
import {
  WorkflowListPage,
  WorkflowBuilderPage,
  WorkflowDetailPage,
} from '@/pages/workflows';

// Segment Pages
import {
  SegmentListPage,
  SegmentBuilderPage,
  SegmentDetailPage,
} from '@/pages/segments';

// Dashboard Page
import { DashboardPage } from '@/pages/dashboard';

// Analytics Pages
import {
  AnalyticsOverviewPage,
  CampaignAnalyticsPage,
  ContactAnalyticsPage,
  FormAnalyticsPage,
  LandingPageAnalyticsPage,
} from '@/pages/analytics';

// CRM Pages
import {
  PipelineKanbanPage,
  DealDetailPage,
  PipelineSettingsPage,
  CompanyListPage,
  CompanyDetailPage,
} from '@/pages/crm';

// Settings Page
import { SettingsPage } from '@/pages/settings';

// Billing Page
import { BillingPage } from '@/pages/billing';
import { DemoCheckoutPage } from '@/pages/billing/DemoCheckoutPage';

// Integrations Page
import { IntegrationsPage } from '@/pages/integrations';

// Accept Invitation Page
import { AcceptInvitationPage } from '@/pages/auth/AcceptInvitationPage';

// Sequence Pages
import {
  SequenceListPage,
  SequenceBuilderPage,
  SequenceDetailPage,
} from '@/pages/sequences';

// Landlord console (platform staff only, cross-tenant)
import { LandlordRoute } from '@/components/auth/LandlordRoute';
import { LandlordLayout } from '@/components/layout/LandlordLayout';
import {
  LandlordOverviewPage,
  TenantListPage,
  TenantDetailPage,
  DeliverabilityPage,
  RevenuePage,
} from '@/pages/landlord';

// Other Pages
import { ProfilePage } from '@/pages/ProfilePage';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const NotFoundPage = () => (
  <div className="flex items-center justify-center h-screen">
    <div className="text-center">
      <h1 className="text-6xl font-bold text-foreground">404</h1>
      <p className="text-xl text-muted-foreground mt-4">Page not found</p>
      <a href="/" className="text-primary hover:underline mt-4 inline-block">
        Go back home
      </a>
    </div>
  </div>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          {/* Followed from a mail client, which may not be the browser
              the account is signed in to, so it is a public route. */}
          <Route path="/verify-email" element={<VerifyEmailPage />} />

          {/* Public form page (no auth required) */}
          <Route path="/f/:id" element={<PublicFormPage />} />

          {/* Accept invitation (no auth required) */}
          <Route path="/accept-invitation" element={<AcceptInvitationPage />} />

          {/* Public landing page (no auth required) - handled by Django backend */}

          {/* Full-screen protected routes (no AppLayout) */}
          <Route
            element={
              <ProtectedRoute>
                <Outlet />
              </ProtectedRoute>
            }
          >
            <Route path="/checkout/demo" element={<DemoCheckoutPage />} />

            {/* The page builder owns the window. Inside AppLayout its
                `h-screen` was measured against a viewport it only started 70px
                into, so the editor overflowed the page and its panels ran off
                the bottom; the app rail also competed with the editor's own
                panels for a canvas that had already shrunk to 57% of the
                width. It keeps its own back arrow as the way out. */}
            <Route
              path="/landing-pages/:id/edit"
              element={<LandingPageBuilderPage />}
            />
          </Route>

          {/* Protected routes */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />

            {/* Contact routes */}
            <Route path="/contacts" element={<ContactListPage />} />
            <Route path="/contacts/new" element={<ContactCreatePage />} />
            <Route path="/contacts/tags" element={<TagManagementPage />} />
            <Route path="/contacts/:id" element={<ContactDetailPage />} />
            <Route path="/contacts/:id/edit" element={<ContactEditPage />} />

            {/* Template routes */}
            <Route path="/templates" element={<TemplateListPage />} />
            <Route path="/templates/new" element={<TemplateEditorPage />} />
            <Route path="/templates/:id/edit" element={<TemplateEditorPage />} />

            {/* Campaign routes */}
            <Route path="/campaigns" element={<CampaignListPage />} />
            <Route path="/campaigns/new" element={<CampaignWizardPage />} />
            <Route path="/campaigns/:id" element={<CampaignDetailPage />} />
            <Route path="/campaigns/:id/edit" element={<CampaignWizardPage />} />

            {/* Form routes */}
            <Route path="/forms" element={<FormListPage />} />
            <Route path="/forms/new" element={<FormBuilderPage />} />
            <Route path="/forms/:id" element={<FormDetailPage />} />
            <Route path="/forms/:id/edit" element={<FormBuilderPage />} />

          <Route path="/popups" element={<PopupListPage />} />
          <Route path="/popups/:id/edit" element={<PopupBuilderPage />} />
          <Route path="/popups/:id/analytics" element={<PopupAnalyticsPage />} />

            {/* Landing Page routes */}
            <Route path="/landing-pages" element={<LandingPageListPage />} />
            <Route path="/landing-pages/:id" element={<LandingPageDetailPage />} />
            <Route path="/landing-pages/:id/preview" element={<LandingPagePreviewPage />} />

            {/* Workflow routes */}
            <Route path="/workflows" element={<WorkflowListPage />} />
            <Route path="/workflows/new" element={<WorkflowBuilderPage />} />
            <Route path="/workflows/:id" element={<WorkflowDetailPage />} />
            <Route path="/workflows/:id/edit" element={<WorkflowBuilderPage />} />

            {/* Segment routes */}
            <Route path="/segments" element={<SegmentListPage />} />
            <Route path="/segments/new" element={<SegmentBuilderPage />} />
            <Route path="/segments/:id" element={<SegmentDetailPage />} />
            <Route path="/segments/:id/edit" element={<SegmentBuilderPage />} />

            {/* CRM routes */}
            <Route path="/crm" element={<PipelineKanbanPage />} />
            <Route path="/crm/deals/:id" element={<DealDetailPage />} />
            <Route path="/crm/settings" element={<PipelineSettingsPage />} />
            <Route path="/crm/companies" element={<CompanyListPage />} />
            <Route path="/crm/companies/:id" element={<CompanyDetailPage />} />

            {/* Sequence routes */}
            <Route path="/sequences" element={<SequenceListPage />} />
            <Route path="/sequences/new" element={<SequenceBuilderPage />} />
            <Route path="/sequences/:id" element={<SequenceDetailPage />} />
            <Route path="/sequences/:id/edit" element={<SequenceBuilderPage />} />

            {/* Analytics routes */}
            <Route path="/analytics" element={<AnalyticsOverviewPage />} />
            <Route path="/analytics/campaigns" element={<CampaignAnalyticsPage />} />
            <Route path="/analytics/campaigns/:id" element={<CampaignAnalyticsPage />} />
            <Route path="/analytics/contacts" element={<ContactAnalyticsPage />} />
            <Route path="/analytics/forms" element={<FormAnalyticsPage />} />
            <Route path="/analytics/landing-pages" element={<LandingPageAnalyticsPage />} />

            {/* Billing routes */}
            <Route path="/billing" element={<BillingPage />} />

            {/* Integrations routes */}
            <Route path="/integrations" element={<IntegrationsPage />} />

            {/* Other routes */}
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>

          {/* Landlord console. Its own layout and its own guard: every screen
              beneath it reads across tenants, so it must not share a shell
              whose navigation assumes the signed-in user has an organization. */}
          <Route
            element={
              <LandlordRoute>
                <LandlordLayout />
              </LandlordRoute>
            }
          >
            <Route path="/landlord" element={<LandlordOverviewPage />} />
            <Route path="/landlord/tenants" element={<TenantListPage />} />
            <Route path="/landlord/tenants/:id" element={<TenantDetailPage />} />
            <Route path="/landlord/deliverability" element={<DeliverabilityPage />} />
            <Route path="/landlord/revenue" element={<RevenuePage />} />
            {/* The operator's own account. It lives in here rather than at
                /profile because an org-less staff user is redirected out of
                the tenant app, and this is the only place they can change
                the password their account was created with. */}
            <Route path="/landlord/profile" element={<ProfilePage />} />
          </Route>

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </QueryClientProvider>
  );
}

export default App;
