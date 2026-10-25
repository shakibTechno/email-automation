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
import { TagChip } from '@/components/contacts/TagChip';
import { useCustomFields } from '@/hooks/useCustomFields';

// ── helpers ──────────────────────────────────────────────────────────────────

function getInitials(contact: { first_name?: string; last_name?: string; email: string }) {
  if (contact.first_name || contact.last_name) {
    return `${contact.first_name?.[0] ?? ''}${contact.last_name?.[0] ?? ''}`.toUpperCase();
  }
  return contact.email[0].toUpperCase();
}

/**
 * Avatars used to pick from six unrelated gradients, which fought the palette.
 * The mark is now the brand chip; only the ring opacity varies by id, so one
 * contact still looks distinct from the next without introducing new hues.
 */
const AVATAR_RINGS = [
  'ring-brand/10',
  'ring-brand/20',
  'ring-brand/30',
  'ring-brand/40',
  'ring-brand/50',
  'ring-brand/60',
];

function avatarRing(id: string) {
  return AVATAR_RINGS[id.charCodeAt(0) % AVATAR_RINGS.length];
}

const SOURCE_META: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  manual:      { label: 'Manual Entry',  icon: UserCheck,  color: 'text-muted-foreground' },
  import:      { label: 'CSV Import',    icon: Upload,     color: 'text-brand' },
  api:         { label: 'API',           icon: Code2,      color: 'text-info' },
  form:        { label: 'Web Form',      icon: FileText,   color: 'text-success' },
  integration: { label: 'Integration',   icon: Plug,       color: 'text-warning' },
};

const ENGAGEMENT_META: Record<string, { label: string; color: string; bar: string; desc: string }> = {
  high:   { label: 'High',   color: 'text-success', bar: 'bg-success', desc: 'Very active — opens and clicks regularly' },
  medium: { label: 'Medium', color: 'text-warning',   bar: 'bg-warning',  desc: 'Occasionally engaged' },
  low:    { label: 'Low',    color: 'text-warning',  bar: 'bg-warning', desc: 'Rarely interacts with emails' },
  none:   { label: 'None',   color: 'text-subtle-foreground',   bar: 'bg-secondary',  desc: 'No engagement recorded yet' },
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
  // With the other hooks, above the early returns: calling it below them
  // makes it conditional, which breaks hook ordering on the renders that
  // return early.
  const { fields: customFields } = useCustomFields();

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
  // Labelled from the definitions rather than shown as raw JSON keys. This
  // used to print whatever key happened to be stored, so a contact showed
  // "annual_revenue" instead of "Annual Revenue" — and showed keys that no
  // longer had a definition at all with no sign that they were orphans.
  const customEntries = Object.entries(contact.custom_fields ?? {})
    .filter(([, v]) => v !== null && v !== '' && !(Array.isArray(v) && !v.length))
    .map(([key, value]) => {
      const definition = customFields.find((f) => f.key === key);
      return {
        key,
        label: definition?.name ?? key,
        orphan: !definition,
        value: Array.isArray(value) ? value.join(', ') : String(value),
      };
    })
    .sort((a, b) => a.label.localeCompare(b.label));

  const displayName =
    contact.first_name || contact.last_name
      ? `${contact.first_name ?? ''} ${contact.last_name ?? ''}`.trim()
      : contact.email;

  return (
    <div className="w-full space-y-3.5">

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
      <Card className="chart-hero">
        <CardContent className="pt-6">
          <div className="flex items-center gap-5">
            {/* avatar */}
            <div
              className={`h-16 w-16 flex-shrink-0 rounded-full bg-brand-fill ring-4 ${avatarRing(contact.id)} flex items-center justify-center`}
            >
              <span className="text-xl font-extrabold tracking-tight text-brand-ink">
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
                  <Badge variant="outline" className="text-success border-success/[.30] bg-success/[.10] gap-1">
                    <CheckCircle2 className="h-3 w-3" /> Subscribed
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-destructive border-destructive/[.30] bg-destructive/[.10] gap-1">
                    <UserX className="h-3 w-3" /> Unsubscribed
                  </Badge>
                )}

                {/* verified */}
                {contact.is_verified ? (
                  <Badge variant="outline" className="text-brand border-info/[.30] bg-info/[.10] gap-1">
                    <ShieldCheck className="h-3 w-3" /> Verified
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-muted-foreground border-border bg-secondary/50 gap-1">
                    <ShieldOff className="h-3 w-3" /> Unverified
                  </Badge>
                )}

                {/* bounced */}
                {contact.bounced_at && (
                  <Badge variant="outline" className="text-warning border-warning/[.30] bg-warning/[.10] gap-1">
                    <AlertTriangle className="h-3 w-3" /> Bounced
                  </Badge>
                )}

                {/* source */}
                <Badge variant="outline" className={`border-border bg-secondary/50 gap-1 ${sourceMeta.color}`}>
                  <SourceIcon className="h-3 w-3" />
                  {sourceMeta.label}
                </Badge>
              </div>
            </div>

            {/* Lead score as a meter: the number alone does not say how close
                this contact is to the next threshold, which is the decision. */}
            <div className="w-full flex-shrink-0 sm:w-[220px]">
              <div className="mb-1.5 flex items-center gap-2">
                <span className="stat-label">Lead score</span>
                <button
                  type="button"
                  onClick={() => setScoreHistoryOpen(true)}
                  className="ml-auto font-mono text-[10.5px] text-subtle-foreground hover:text-brand"
                >
                  history →
                </button>
              </div>

              <button
                type="button"
                onClick={() => setScoreHistoryOpen(true)}
                className="w-full text-left"
              >
                <div className="flex items-baseline gap-1.5">
                  <span className="stat-value text-[26px] leading-none">
                    {contact.lead_score ?? 0}
                  </span>
                  <span className="text-[13px] text-subtle-foreground">/ 100</span>
                  <span className="ml-auto">
                    <ScoreBadge
                      score={contact.lead_score}
                      engagementLevel={contact.engagement_level}
                    />
                  </span>
                </div>

                <div className="bar-track mt-2">
                  <div
                    className="bar-fill"
                    style={{ width: `${Math.min(100, Math.max(0, contact.lead_score ?? 0))}%` }}
                  />
                </div>
                <div className="mt-1 flex justify-between font-mono text-[9.5px] text-subtle-foreground">
                  <span>cold 10</span>
                  <span>warm 40</span>
                  <span>hot 70</span>
                </div>
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── main grid ── */}
      <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">

        {/* ── LEFT: detail card ── */}
        <Card className="md:col-span-2">
          <CardContent className="pt-6 space-y-1">

            <SectionHeading>Contact Info</SectionHeading>
            <InfoRow icon={Mail} label="Email" iconClass="text-brand">
              <span className="font-mono text-sm">{contact.email}</span>
            </InfoRow>
            {contact.phone && (
              <InfoRow icon={Phone} label="Phone" iconClass="text-success">
                {contact.phone}
              </InfoRow>
            )}
            {contact.company && (
              <InfoRow icon={Briefcase} label="Company" iconClass="text-info">
                {contact.company}
              </InfoRow>
            )}
            {contact.job_title && (
              <InfoRow icon={Globe} label="Job Title" iconClass="text-brand">
                {contact.job_title}
              </InfoRow>
            )}
            <InfoRow icon={User} label="Assigned To" iconClass="text-brand">
              {contact.assigned_to_name ?? (
                <span className="text-muted-foreground italic">Unassigned</span>
              )}
            </InfoRow>

            <SectionHeading>Engagement</SectionHeading>
            <InfoRow icon={Activity} label="Engagement" iconClass={engagementMeta.color}>
              <div className="space-y-1">
                <div className={`font-semibold ${engagementMeta.color}`}>{engagementMeta.label}</div>
                <div className="h-1.5 w-32 rounded-full bg-secondary overflow-hidden">
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
              <InfoRow icon={UserX} label="Unsubscribed" iconClass="text-destructive">
                {formatDateTime(contact.unsubscribed_at)}
              </InfoRow>
            )}
            {contact.bounced_at && (
              <InfoRow icon={AlertTriangle} label="Bounced At" iconClass="text-warning">
                {formatDateTime(contact.bounced_at)}
              </InfoRow>
            )}

            {/* Tags */}
            {tags.length > 0 && (
              <>
                <SectionHeading>Tags</SectionHeading>
                <div className="flex flex-wrap gap-2 py-2">
                  {tags.map((tag) => (
                    <TagChip key={tag.id} tag={tag} />
                  ))}
                </div>
              </>
            )}

            {/* Custom Fields */}
            {customEntries.length > 0 && (
              <>
                <SectionHeading>Custom Fields</SectionHeading>
                {customEntries.map((entry) => (
                  <InfoRow
                    key={entry.key}
                    icon={FileText}
                    label={entry.label}
                    iconClass="text-subtle-foreground"
                  >
                    {entry.value}
                    {/* A value whose definition was deleted. Shown rather than
                        hidden, because silently dropping stored data is worse
                        than showing it as unrecognised. */}
                    {entry.orphan && (
                      <span className="ml-2 text-[11px] text-muted-foreground">
                        (no longer a defined field)
                      </span>
                    )}
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
            {/* Lead score lives in the hero meter now; repeating it here was
                the same figure twice on one screen. */}
            <CardContent className="flex gap-6">
              <div>
                <div className="stat-value text-[20px]">{tags.length}</div>
                <div className="stat-label">Tags</div>
              </div>
              <div>
                <div className="stat-value text-[20px]">{contactDeals?.length ?? 0}</div>
                <div className="stat-label">Deals</div>
              </div>
              {customEntries.length > 0 && (
                <div>
                  <div className="stat-value text-[20px]">{customEntries.length}</div>
                  <div className="stat-label">Custom fields</div>
                </div>
              )}
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
                      className="flex items-center justify-between p-2 rounded-md hover:bg-secondary/50 cursor-pointer transition-colors"
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
