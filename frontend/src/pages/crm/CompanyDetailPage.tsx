import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Building2,
  Globe,
  Phone,
  MapPin,
  Users,
  Briefcase,
  Activity as ActivityIcon,
  ArrowLeft,
  Pencil,
  DollarSign,
  ChevronRight,
  CheckCircle2,
  Clock,
  PhoneCall,
  Mail,
  CalendarCheck,
  FileText,
  StickyNote,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { CompanyFormDialog } from '@/components/crm/CompanyFormDialog';
import {
  useCompany,
  useCompanyContacts,
  useCompanyDeals,
  useCompanyActivities,
  useCompanyMutations,
} from '@/hooks/useCRM';
import { CreateCompanyData, DealListItem, ActivityListItem } from '@/types/crm';
import { cn } from '@/lib/utils';

const INDUSTRY_LABELS: Record<string, string> = {
  technology: 'Technology',
  financial_services: 'Financial Services',
  healthcare: 'Healthcare',
  retail: 'Retail',
  manufacturing: 'Manufacturing',
  real_estate: 'Real Estate',
  education: 'Education',
  media: 'Media & Entertainment',
  consulting: 'Consulting',
  other: 'Other',
};

const DEAL_STATUS_COLORS: Record<string, string> = {
  open: 'bg-blue-100 text-blue-700',
  won: 'bg-green-100 text-green-700',
  lost: 'bg-red-100 text-red-700',
};

const ACTIVITY_ICONS: Record<string, React.ElementType> = {
  call: PhoneCall,
  email: Mail,
  meeting: CalendarCheck,
  task: FileText,
  note: StickyNote,
};

const DealRow = ({ deal }: { deal: DealListItem }) => (
  <Link
    to={`/crm/deals/${deal.id}`}
    className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 border border-transparent hover:border-gray-200 transition-colors group"
  >
    <div className="flex items-center gap-3 min-w-0">
      <Briefcase className="h-4 w-4 text-gray-400 flex-shrink-0" />
      <div className="min-w-0">
        <p className="font-medium text-sm text-gray-900 truncate">{deal.title}</p>
        <p className="text-xs text-gray-500">{deal.stage_name}</p>
      </div>
    </div>
    <div className="flex items-center gap-3 flex-shrink-0">
      <Badge className={cn('text-xs', DEAL_STATUS_COLORS[deal.status])}>
        {deal.status}
      </Badge>
      <span className="text-sm font-medium text-gray-900">
        ${Number(deal.value).toLocaleString()}
      </span>
      <ChevronRight className="h-4 w-4 text-gray-300 group-hover:text-gray-500" />
    </div>
  </Link>
);

const ActivityRow = ({ activity }: { activity: ActivityListItem }) => {
  const Icon = ACTIVITY_ICONS[activity.activity_type] ?? ActivityIcon;
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50">
      <div className="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5">
        <Icon className="h-4 w-4 text-gray-500" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="font-medium text-sm text-gray-900 truncate">{activity.title}</p>
          {activity.is_completed ? (
            <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
          ) : (
            <Clock className="h-4 w-4 text-gray-400 flex-shrink-0" />
          )}
        </div>
        {activity.description && (
          <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{activity.description}</p>
        )}
        <div className="flex items-center gap-2 mt-1">
          <span className="text-xs text-gray-400 capitalize">{activity.activity_type}</span>
          {activity.deal_title && (
            <>
              <span className="text-xs text-gray-300">·</span>
              <span className="text-xs text-gray-400">{activity.deal_title}</span>
            </>
          )}
          <span className="text-xs text-gray-300">·</span>
          <span className="text-xs text-gray-400">
            {new Date(activity.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  );
};

export const CompanyDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showEdit, setShowEdit] = useState(false);

  const { data: company, isLoading } = useCompany(id!);
  const { data: contacts = [] } = useCompanyContacts(id!);
  const { data: deals = [] } = useCompanyDeals(id!);
  const { data: activities = [] } = useCompanyActivities(id!);
  const { updateCompany, isUpdating } = useCompanyMutations();

  const handleUpdate = async (data: CreateCompanyData) => {
    if (!id) return;
    await updateCompany(id, data);
    setShowEdit(false);
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!company) {
    return (
      <div className="p-6 text-center text-gray-500">
        <Building2 className="h-10 w-10 mx-auto mb-2 text-gray-300" />
        <p>Company not found.</p>
        <Button variant="link" onClick={() => navigate('/crm/companies')}>
          Back to Companies
        </Button>
      </div>
    );
  }

  const openDeals = deals.filter((d) => d.status === 'open');
  const openValue = openDeals.reduce((sum, d) => sum + Number(d.value), 0);

  return (
    <div className="p-6 space-y-6">
      {/* Back nav */}
      <Button
        variant="ghost"
        size="sm"
        className="gap-2 -ml-2 text-gray-600"
        onClick={() => navigate('/crm/companies')}
      >
        <ArrowLeft className="h-4 w-4" />
        Companies
      </Button>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="h-14 w-14 rounded-full bg-indigo-100 flex items-center justify-center">
            <Building2 className="h-7 w-7 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">{company.name}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              {company.industry && (
                <Badge variant="secondary" className="text-xs">
                  {INDUSTRY_LABELS[company.industry] ?? company.industry}
                </Badge>
              )}
              {company.size && (
                <span className="text-sm text-gray-500">{company.size} employees</span>
              )}
            </div>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowEdit(true)}>
          <Pencil className="h-4 w-4 mr-2" />
          Edit
        </Button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{contacts.length}</p>
          <p className="text-sm text-gray-500 mt-1">Contacts</p>
        </div>
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{deals.length}</p>
          <p className="text-sm text-gray-500 mt-1">Total Deals</p>
        </div>
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-2xl font-bold text-green-700">${openValue.toLocaleString()}</p>
          <p className="text-sm text-gray-500 mt-1">Open Pipeline</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left — Info */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg border p-4 space-y-3">
            <h3 className="text-sm font-semibold text-gray-700">Company Info</h3>

            {company.website && (
              <div className="flex items-center gap-2 text-sm">
                <Globe className="h-4 w-4 text-gray-400" />
                <a
                  href={company.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 hover:underline truncate"
                >
                  {company.website}
                </a>
              </div>
            )}
            {company.phone && (
              <div className="flex items-center gap-2 text-sm text-gray-700">
                <Phone className="h-4 w-4 text-gray-400" />
                {company.phone}
              </div>
            )}
            {company.address && (
              <div className="flex items-start gap-2 text-sm text-gray-700">
                <MapPin className="h-4 w-4 text-gray-400 mt-0.5" />
                <span className="whitespace-pre-line">{company.address}</span>
              </div>
            )}
            {company.annual_revenue !== null && company.annual_revenue !== undefined && (
              <div className="flex items-center gap-2 text-sm text-gray-700">
                <DollarSign className="h-4 w-4 text-gray-400" />
                ${Number(company.annual_revenue).toLocaleString()} / year
              </div>
            )}
            {company.owner_name && (
              <div className="flex items-center gap-2 text-sm text-gray-700">
                <Users className="h-4 w-4 text-gray-400" />
                <span className="text-xs text-gray-500">Owner:</span> {company.owner_name}
              </div>
            )}
            {company.description && (
              <p className="text-sm text-gray-600 border-t pt-3">{company.description}</p>
            )}
          </div>
        </div>

        {/* Right — Tabs */}
        <div className="col-span-2">
          <Tabs defaultValue="contacts">
            <TabsList>
              <TabsTrigger value="contacts">
                Contacts ({contacts.length})
              </TabsTrigger>
              <TabsTrigger value="deals">
                Deals ({deals.length})
              </TabsTrigger>
              <TabsTrigger value="activities">
                Activities ({activities.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="contacts" className="mt-4">
              {contacts.length === 0 ? (
                <div className="text-center py-10 text-gray-500">
                  <Users className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">No contacts linked to this company.</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {contacts.map((c: any) => (
                    <Link
                      key={c.id}
                      to={`/contacts/${c.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 border border-transparent hover:border-gray-200 transition-colors group"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center text-sm font-medium text-gray-600 flex-shrink-0">
                          {(c.first_name?.[0] || c.email?.[0] || '?').toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium text-sm text-gray-900">
                            {c.first_name || c.last_name
                              ? `${c.first_name} ${c.last_name}`.trim()
                              : c.email}
                          </p>
                          <p className="text-xs text-gray-500">{c.email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {c.job_title && (
                          <span className="text-xs text-gray-500">{c.job_title}</span>
                        )}
                        <ChevronRight className="h-4 w-4 text-gray-300 group-hover:text-gray-500" />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="deals" className="mt-4">
              {deals.length === 0 ? (
                <div className="text-center py-10 text-gray-500">
                  <Briefcase className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">No deals linked to this company.</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {deals.map((deal) => (
                    <DealRow key={deal.id} deal={deal} />
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="activities" className="mt-4">
              {activities.length === 0 ? (
                <div className="text-center py-10 text-gray-500">
                  <ActivityIcon className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">No activities found for this company.</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {activities.map((activity) => (
                    <ActivityRow key={activity.id} activity={activity} />
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Edit dialog */}
      <CompanyFormDialog
        open={showEdit}
        onClose={() => setShowEdit(false)}
        onSubmit={handleUpdate}
        initialValues={company}
        isSubmitting={isUpdating}
      />
    </div>
  );
};
