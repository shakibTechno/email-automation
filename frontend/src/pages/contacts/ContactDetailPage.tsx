import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Edit,
  Mail,
  Phone,
  Briefcase,
  Calendar,
  Activity,
  Plus,
  ShieldCheck,
  ShieldOff,
  Globe,
  Upload,
  Code2,
  FileText,
  Plug,
  User,
  UserCheck,
  UserX,
  AlertTriangle,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useContact } from '@/hooks/useContacts';
import { useContactDeals } from '@/hooks/useCRM';
import { DealStatusBadge } from '@/components/crm/DealStatusBadge';
import { ScoreBadge } from '@/components/lead-scoring/ScoreBadge';
import { ScoreHistoryDrawer } from '@/components/lead-scoring/ScoreHistoryDrawer';
import { ContactActivityTimeline } from '@/components/contacts/ContactActivityTimeline';
import { formatDateTime } from '@/lib/utils';

// ── helpers ──────────────────────────────────────────────────────────────────

function getInitials(contact: { first_name?: string; last_name?: string; email: string }) {
  if (contact.first_name || contact.last_name) {
    return `${contact.first_name?.[0] ?? ''}${contact.last_name?.[0] ?? ''}`.toUpperCase();
  }
  return contact.email[0].toUpperCase();
}

const AVATAR_COLORS = [
  'from-violet-500 to-purple-600',
  'from-blue-500 to-cyan-500',
  'from-emerald-500 to-teal-600',
  'from-orange-400 to-rose-500',
  'from-pink-500 to-fuchsia-600',
  'from-amber-400 to-orange-500',
];

function avatarGradient(id: string) {
  const idx = id.charCodeAt(0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}

const SOURCE_META: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  manual:      { label: 'Manual Entry',  icon: UserCheck,  color: 'text-slate-500' },
  import:      { label: 'CSV Import',    icon: Upload,     color: 'text-blue-500' },
  api:         { label: 'API',           icon: Code2,      color: 'text-purple-500' },
  form:        { label: 'Web Form',      icon: FileText,   color: 'text-emerald-500' },
  integration: { label: 'Integration',   icon: Plug,       color: 'text-orange-500' },
};

const ENGAGEMENT_META: Record<string, { label: string; color: string; bar: string; desc: string }> = {
  high:   { label: 'High',   color: 'text-emerald-600', bar: 'bg-emerald-500', desc: 'Very active — opens and clicks regularly' },
  medium: { label: 'Medium', color: 'text-amber-600',   bar: 'bg-amber-400',  desc: 'Occasionally engaged' },
  low:    { label: 'Low',    color: 'text-orange-600',  bar: 'bg-orange-400', desc: 'Rarely interacts with emails' },
  none:   { label: 'None',   color: 'text-slate-400',   bar: 'bg-slate-200',  desc: 'No engagement recorded yet' },
};

const ENGAGEMENT_BAR_WIDTH: Record<string, string> = {
  high: 'w-full', medium: 'w-2/3', low: 'w-1/3', none: 'w-0',
};

function InfoRow({
  icon: Icon,
  label,
  children,
  iconClass = 'text-muted-foreground',
}: {
  icon: React.ElementType;
  label: string;
  children: React.ReactNode;
  iconClass?: string;
}) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b last:border-0">
      <Icon className={`h-4 w-4 mt-0.5 flex-shrink-0 ${iconClass}`} />
      <div className="min-w-0 flex-1 grid grid-cols-[120px_1fr] gap-2 items-start">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="text-sm font-medium break-words">{children}</span>
      </div>
    </div>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <div className="pt-4 pb-1">
      <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        {children}
      </div>
    </div>
  );
}

// ── component ─────────────────────────────────────────────────────────────────

export const ContactDetailPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const contactId = id || '';
  const { contact, isLoading } = useContact(contactId);
  const { data: contactDeals } = useContactDeals(contactId);
  const [scoreHistoryOpen, setScoreHistoryOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!contact) {
    return (
      <div className="p-6 text-center">
        <h2 className="text-2xl font-bold">Contact not found</h2>
        <Button onClick={() => navigate('/contacts')} className="mt-4">
          Back to Contacts
        </Button>
      </div>
    );
  }

  const tags = contact.tag_details || contact.tags || [];
  const source = contact.source ?? 'manual';
  const sourceMeta = SOURCE_META[source] ?? SOURCE_META.manual;
  const SourceIcon = sourceMeta.icon;
  const engagementMeta = ENGAGEMENT_META[contact.engagement_level] ?? ENGAGEMENT_META.none;
  const customEntries = Object.entries(contact.custom_fields ?? {}).filter(
    ([, v]) => v !== null && v !== ''
  );

  const displayName =
    contact.first_name || contact.last_name
      ? `${contact.first_name ?? ''} ${contact.last_name ?? ''}`.trim()
      : contact.email;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">

      {/* ── top nav ── */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => navigate('/contacts')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Contacts
        </Button>
        <Button onClick={() => navigate(`/contacts/${contactId}/edit`)}>
          <Edit className="h-4 w-4 mr-2" />
          Edit Contact
        </Button>
      </div>

      {/* ── hero / identity ── */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-5">
            {/* avatar */}
            <div
              className={`h-16 w-16 rounded-full bg-gradient-to-br ${avatarGradient(contact.id)} flex items-center justify-center flex-shrink-0 shadow-md`}
            >
              <span className="text-white text-xl font-bold tracking-wide">
                {getInitials(contact)}
              </span>
            </div>

            {/* identity */}
            <div className="min-w-0 flex-1">
              <h1 className="text-2xl font-bold truncate">{displayName}</h1>
              {(contact.job_title || contact.company) && (
                <p className="text-muted-foreground text-sm mt-0.5">
                  {[contact.job_title, contact.company].filter(Boolean).join(' · ')}
                </p>
              )}
              <div className="flex flex-wrap items-center gap-2 mt-2">
                {/* subscription */}
                {contact.is_subscribed ? (
                  <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50 gap-1">
                    <CheckCircle2 className="h-3 w-3" /> Subscribed
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50 gap-1">
                    <UserX className="h-3 w-3" /> Unsubscribed
                  </Badge>
                )}

                {/* verified */}
                {contact.is_verified ? (
                  <Badge variant="outline" className="text-blue-600 border-blue-200 bg-blue-50 gap-1">
                    <ShieldCheck className="h-3 w-3" /> Verified
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-slate-500 border-slate-200 bg-slate-50 gap-1">
                    <ShieldOff className="h-3 w-3" /> Unverified
                  </Badge>
                )}

                {/* bounced */}
                {contact.bounced_at && (
                  <Badge variant="outline" className="text-orange-600 border-orange-200 bg-orange-50 gap-1">
                    <AlertTriangle className="h-3 w-3" /> Bounced
                  </Badge>
                )}

                {/* source */}
                <Badge variant="outline" className={`border-slate-200 bg-slate-50 gap-1 ${sourceMeta.color}`}>
                  <SourceIcon className="h-3 w-3" />
                  {sourceMeta.label}
                </Badge>
              </div>
            </div>

            {/* lead score — prominent */}
            <div className="flex-shrink-0 text-right">
              <div className="text-xs text-muted-foreground mb-1">Lead Score</div>
              <ScoreBadge
                score={contact.lead_score}
                engagementLevel={contact.engagement_level}
                onClick={() => setScoreHistoryOpen(true)}
              />
              <div className="text-[10px] text-muted-foreground mt-1 cursor-pointer hover:text-primary"
                onClick={() => setScoreHistoryOpen(true)}>
                View history →
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── main grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

        {/* ── LEFT: detail card ── */}
        <Card className="md:col-span-2">
          <CardContent className="pt-6 space-y-1">

            <SectionHeading>Contact Info</SectionHeading>
            <InfoRow icon={Mail} label="Email" iconClass="text-blue-500">
              <span className="font-mono text-sm">{contact.email}</span>
            </InfoRow>
            {contact.phone && (
              <InfoRow icon={Phone} label="Phone" iconClass="text-green-500">
                {contact.phone}
              </InfoRow>
            )}
            {contact.company && (
              <InfoRow icon={Briefcase} label="Company" iconClass="text-purple-500">
                {contact.company}
              </InfoRow>
            )}
            {contact.job_title && (
              <InfoRow icon={Globe} label="Job Title" iconClass="text-indigo-500">
                {contact.job_title}
              </InfoRow>
            )}
            <InfoRow icon={User} label="Assigned To" iconClass="text-blue-500">
              {contact.assigned_to_name ?? (
                <span className="text-muted-foreground italic">Unassigned</span>
              )}
            </InfoRow>

            <SectionHeading>Engagement</SectionHeading>
            <InfoRow icon={Activity} label="Engagement" iconClass={engagementMeta.color}>
              <div className="space-y-1">
                <div className={`font-semibold ${engagementMeta.color}`}>{engagementMeta.label}</div>
                <div className="h-1.5 w-32 rounded-full bg-slate-100 overflow-hidden">
                  <div className={`h-full rounded-full ${engagementMeta.bar} ${ENGAGEMENT_BAR_WIDTH[contact.engagement_level]} transition-all`} />
                </div>
                <div className="text-xs text-muted-foreground">{engagementMeta.desc}</div>
              </div>
            </InfoRow>

            <SectionHeading>Lead & Source</SectionHeading>
            <InfoRow icon={SourceIcon} label="Lead Source" iconClass={sourceMeta.color}>
              {sourceMeta.label}
            </InfoRow>
            {contact.unsubscribed_at && (
              <InfoRow icon={UserX} label="Unsubscribed" iconClass="text-red-500">
                {formatDateTime(contact.unsubscribed_at)}
              </InfoRow>
            )}
            {contact.bounced_at && (
              <InfoRow icon={AlertTriangle} label="Bounced At" iconClass="text-orange-500">
                {formatDateTime(contact.bounced_at)}
              </InfoRow>
            )}

            {/* Tags */}
            {tags.length > 0 && (
              <>
                <SectionHeading>Tags</SectionHeading>
                <div className="flex flex-wrap gap-2 py-2">
                  {tags.map((tag) => (
                    <Badge
                      key={tag.id}
                      style={{ backgroundColor: tag.color }}
                      className="text-white border-0"
                    >
                      {tag.name}
                    </Badge>
                  ))}
                </div>
              </>
            )}

            {/* Custom Fields */}
            {customEntries.length > 0 && (
              <>
                <SectionHeading>Custom Fields</SectionHeading>
                {customEntries.map(([key, value]) => (
                  <InfoRow key={key} icon={FileText} label={key} iconClass="text-slate-400">
                    {String(value)}
                  </InfoRow>
                ))}
              </>
            )}

            {/* Activity Timeline */}
            <SectionHeading>Activity Timeline</SectionHeading>
            <div className="pt-2">
              <ContactActivityTimeline contactId={contactId} />
            </div>

          </CardContent>
        </Card>

        {/* ── RIGHT: sidebar ── */}
        <div className="space-y-6">

          {/* Metadata */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Record Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-start gap-2">
                <Calendar className="h-3.5 w-3.5 mt-0.5 text-muted-foreground flex-shrink-0" />
                <div>
                  <div className="text-xs text-muted-foreground">Created</div>
                  <div className="font-medium text-xs">{formatDateTime(contact.created_at)}</div>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <Clock className="h-3.5 w-3.5 mt-0.5 text-muted-foreground flex-shrink-0" />
                <div>
                  <div className="text-xs text-muted-foreground">Last Updated</div>
                  <div className="font-medium text-xs">{formatDateTime(contact.updated_at)}</div>
                </div>
              </div>
              {contact.last_activity_at && (
                <div className="flex items-start gap-2">
                  <Activity className="h-3.5 w-3.5 mt-0.5 text-muted-foreground flex-shrink-0" />
                  <div>
                    <div className="text-xs text-muted-foreground">Last Activity</div>
                    <div className="font-medium text-xs">{formatDateTime(contact.last_activity_at)}</div>
                  </div>
                </div>
              )}
              <div className="flex items-start gap-2">
                <SourceIcon className={`h-3.5 w-3.5 mt-0.5 flex-shrink-0 ${sourceMeta.color}`} />
                <div>
                  <div className="text-xs text-muted-foreground">Lead Source</div>
                  <div className="font-medium text-xs">{sourceMeta.label}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Quick Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Lead Score</div>
                <ScoreBadge
                  score={contact.lead_score}
                  engagementLevel={contact.engagement_level}
                  onClick={() => setScoreHistoryOpen(true)}
                />
              </div>
              <div className="flex gap-4">
                <div>
                  <div className="text-lg font-bold">{tags.length}</div>
                  <div className="text-xs text-muted-foreground">Tags</div>
                </div>
                <div>
                  <div className="text-lg font-bold">{contactDeals?.length ?? 0}</div>
                  <div className="text-xs text-muted-foreground">Deals</div>
                </div>
                {customEntries.length > 0 && (
                  <div>
                    <div className="text-lg font-bold">{customEntries.length}</div>
                    <div className="text-xs text-muted-foreground">Custom fields</div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Deals */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm">Deals</CardTitle>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => navigate(`/crm?contact=${contactId}`)}
              >
                <Plus className="h-3 w-3 mr-1" />
                New
              </Button>
            </CardHeader>
            <CardContent>
              {!contactDeals || contactDeals.length === 0 ? (
                <div className="text-xs text-muted-foreground">No deals linked yet</div>
              ) : (
                <div className="space-y-2">
                  {contactDeals.map((deal) => (
                    <div
                      key={deal.id}
                      className="flex items-center justify-between p-2 rounded-md hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/crm/deals/${deal.id}`)}
                    >
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{deal.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {deal.stage_name} &middot;{' '}
                          {deal.value > 0 ? `$${deal.value.toLocaleString()}` : 'No value'}
                        </div>
                      </div>
                      <DealStatusBadge status={deal.status} />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <ScoreHistoryDrawer
        contactId={contactId}
        currentScore={contact.lead_score}
        open={scoreHistoryOpen}
        onClose={() => setScoreHistoryOpen(false)}
      />
    </div>
  );
};
