import { useState, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  ArrowLeft, CheckCircle2, Copy, Tag as TagIcon,
  TrendingUp, Calendar, AlertTriangle,
} from 'lucide-react';
import { useDuplicateContacts, useMergeContacts } from '@/hooks/useContacts';
import { DuplicateGroup, Contact } from '@/types/contact';
import { cn, formatDate } from '@/lib/utils';
import { TagChip } from '@/components/contacts/TagChip';

// ── avatar helpers ─────────────────────────────────────────────────────────────
const AVATAR_GRADIENTS = [
  'from-violet-500 to-purple-600',
  'from-blue-500 to-cyan-500',
  'from-emerald-500 to-teal-600',
  'from-orange-400 to-rose-500',
  'from-pink-500 to-fuchsia-600',
];

function initials(c: Contact) {
  if (c.first_name || c.last_name)
    return `${c.first_name?.[0] ?? ''}${c.last_name?.[0] ?? ''}`.toUpperCase();
  return c.email[0].toUpperCase();
}

function Avatar({ contact, idx, size = 'md' }: { contact: Contact; idx: number; size?: 'sm' | 'md' }) {
  const grad = AVATAR_GRADIENTS[idx % AVATAR_GRADIENTS.length];
  const cls = size === 'sm'
    ? 'h-7 w-7 text-xs'
    : 'h-10 w-10 text-sm';
  return (
    <div className={cn(
      'rounded-full bg-gradient-to-br flex items-center justify-center text-white font-semibold flex-shrink-0',
      grad, cls
    )}>
      {initials(contact)}
    </div>
  );
}

// ── list view ──────────────────────────────────────────────────────────────────
function GroupCard({ group, onMerge }: { group: DuplicateGroup; onMerge: () => void }) {
  return (
    <div className="flex items-center gap-4 p-4 rounded-lg border bg-card hover:bg-accent/40 transition-colors">
      {/* overlapping avatars */}
      <div className="flex -space-x-2 flex-shrink-0">
        {group.contacts.slice(0, 3).map((c, i) => (
          <div key={c.id} className="ring-2 ring-background rounded-full">
            <Avatar contact={c} idx={i} size="sm" />
          </div>
        ))}
        {group.contacts.length > 3 && (
          <div className="h-7 w-7 rounded-full ring-2 ring-background bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
            +{group.contacts.length - 3}
          </div>
        )}
      </div>

      {/* info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm truncate">{group.email}</span>
          <Badge variant="outline" className="text-xs bg-warning/[.10] text-warning border-warning/[.30] flex-shrink-0">
            {group.count} duplicates
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">
          {group.contacts.map(c =>
            c.first_name || c.last_name
              ? `${c.first_name ?? ''} ${c.last_name ?? ''}`.trim()
              : '(no name)'
          ).join(' · ')}
        </div>
      </div>

      <Button size="sm" variant="outline" onClick={onMerge} className="flex-shrink-0">
        <Copy className="h-3.5 w-3.5 mr-1.5" />
        Merge
      </Button>
    </div>
  );
}

// ── contact picker card ────────────────────────────────────────────────────────
function ContactPickerCard({
  contact,
  idx,
  selected,
  onSelect,
}: {
  contact: Contact;
  idx: number;
  selected: boolean;
  onSelect: () => void;
}) {
  const tags = (contact.tag_details ?? contact.tags ?? []);

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full text-left rounded-lg border p-4 transition-all',
        selected
          ? 'border-primary bg-primary/5 ring-1 ring-primary'
          : 'border-border hover:border-muted-foreground/50 hover:bg-accent/30'
      )}
    >
      <div className="flex items-start gap-3">
        <div className="relative flex-shrink-0">
          <Avatar contact={contact} idx={idx} />
          {selected && (
            <CheckCircle2 className="h-4 w-4 text-primary absolute -bottom-1 -right-1 bg-background rounded-full" />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm">
              {(contact.first_name || contact.last_name)
                ? `${contact.first_name ?? ''} ${contact.last_name ?? ''}`.trim()
                : '(No name)'}
            </span>
            {selected && (
              <Badge className="text-xs h-5 bg-primary text-primary-foreground">Primary</Badge>
            )}
          </div>
          {contact.company && (
            <div className="text-xs text-muted-foreground">{contact.company}</div>
          )}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <TrendingUp className="h-3 w-3" />
              Score: <span className="font-medium text-foreground">{contact.lead_score}</span>
            </div>
            {tags.length > 0 && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TagIcon className="h-3 w-3" />
                <span className="font-medium text-foreground">{tags.length}</span> tags
              </div>
            )}
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Calendar className="h-3 w-3" />
              {formatDate(contact.created_at)}
            </div>
          </div>
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {tags.slice(0, 4).map(tag => (
                <TagChip key={tag.id} tag={tag} size="sm" />
              ))}
              {tags.length > 4 && (
                <span className="text-[10px] text-muted-foreground">+{tags.length - 4}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}

// ── merge view ─────────────────────────────────────────────────────────────────
function MergeView({
  group,
  onBack,
  onMerged,
}: {
  group: DuplicateGroup;
  onBack: () => void;
  onMerged: () => void;
}) {
  const [primaryId, setPrimaryId] = useState(group.contacts[0].id);
  const { mutate: merge, isPending } = useMergeContacts();

  const primary = group.contacts.find(c => c.id === primaryId)!;
  const duplicates = group.contacts.filter(c => c.id !== primaryId);

  const summary = useMemo(() => {
    const maxScore = Math.max(...group.contacts.map(c => c.lead_score));
    const allTagIds = new Set<string>();
    group.contacts.forEach(c => {
      (c.tag_details ?? c.tags ?? []).forEach(t => allTagIds.add(t.id));
    });
    const activities = group.contacts
      .map(c => c.last_activity_at)
      .filter(Boolean) as string[];
    const latestActivity = activities.length
      ? activities.reduce((a, b) => (a > b ? a : b))
      : null;
    return { maxScore, tagCount: allTagIds.size, latestActivity };
  }, [group]);

  const handleMerge = () => {
    merge(
      {
        primary_contact_id: primaryId,
        duplicate_contact_ids: duplicates.map(c => c.id),
      },
      { onSuccess: onMerged }
    );
  };

  return (
    <div className="flex flex-col gap-4 min-h-0">
      <DialogHeader>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <DialogTitle>Merge Duplicates</DialogTitle>
            <DialogDescription className="font-mono text-xs mt-0.5">
              {group.email}
            </DialogDescription>
          </div>
        </div>
      </DialogHeader>

      <p className="text-sm text-muted-foreground">
        Select the <span className="font-semibold text-foreground">primary contact</span> to keep.
        The others will be soft-deleted after merging their tags and data into it.
      </p>

      {/* contact picker */}
      <div className="grid gap-3 overflow-y-auto pr-1" style={{ maxHeight: '340px' }}>
        {group.contacts.map((contact, idx) => (
          <ContactPickerCard
            key={contact.id}
            contact={contact}
            idx={idx}
            selected={contact.id === primaryId}
            onSelect={() => setPrimaryId(contact.id)}
          />
        ))}
      </div>

      {/* merge summary */}
      <div className="rounded-lg border bg-muted/40 p-4 space-y-2">
        <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">
          After Merge
        </div>
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div className="text-center">
            <div className="text-lg font-bold text-warning">{summary.maxScore}</div>
            <div className="text-xs text-muted-foreground">Lead score (highest)</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-brand">{summary.tagCount}</div>
            <div className="text-xs text-muted-foreground">Tags (combined)</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-success">{duplicates.length}</div>
            <div className="text-xs text-muted-foreground">Records removed</div>
          </div>
        </div>
        {summary.latestActivity && (
          <div className="text-xs text-muted-foreground text-center pt-1">
            Last activity: {formatDate(summary.latestActivity)} (most recent kept)
          </div>
        )}
      </div>

      <div className="flex items-start gap-2 rounded-md bg-warning/[.10] border border-warning/[.30] px-3 py-2">
        <AlertTriangle className="h-4 w-4 text-warning flex-shrink-0 mt-0.5" />
        <p className="text-xs text-warning">
          <strong>{primary.first_name || primary.email}</strong> will be kept.{' '}
          {duplicates.length} contact{duplicates.length > 1 ? 's' : ''} will be permanently removed from your list.
        </p>
      </div>

      <div className="flex gap-2 pt-1">
        <Button variant="outline" className="flex-1" onClick={onBack} disabled={isPending}>
          Cancel
        </Button>
        <Button
          className="flex-1"
          onClick={handleMerge}
          disabled={isPending}
        >
          {isPending ? 'Merging…' : `Merge ${group.count} Contacts`}
        </Button>
      </div>
    </div>
  );
}

// ── list view ──────────────────────────────────────────────────────────────────
function ListView({ onSelectGroup }: { onSelectGroup: (g: DuplicateGroup) => void }) {
  const { data, isLoading } = useDuplicateContacts();

  return (
    <div className="flex flex-col gap-4 min-h-0">
      <DialogHeader>
        <DialogTitle>Duplicate Contacts</DialogTitle>
        <DialogDescription>
          {isLoading
            ? 'Scanning for duplicate email addresses…'
            : data?.total_groups
            ? `Found ${data.total_groups} group${data.total_groups > 1 ? 's' : ''} of duplicate contacts.`
            : 'No duplicate contacts found.'}
        </DialogDescription>
      </DialogHeader>

      <div className="overflow-y-auto space-y-2 pr-1 flex-1" style={{ maxHeight: '460px' }}>
        {isLoading ? (
          [...Array(3)].map((_, i) => (
            <div key={i} className="flex items-center gap-4 p-4 rounded-lg border">
              <div className="flex -space-x-2">
                {[0, 1].map(j => <Skeleton key={j} className="h-7 w-7 rounded-full ring-2 ring-background" />)}
              </div>
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-3 w-32" />
              </div>
              <Skeleton className="h-8 w-20" />
            </div>
          ))
        ) : data?.total_groups === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <CheckCircle2 className="h-12 w-12 text-success mb-3" />
            <p className="font-medium">No duplicates found</p>
            <p className="text-sm text-muted-foreground mt-1">
              Your contact list is clean — every email address is unique.
            </p>
          </div>
        ) : (
          data?.duplicate_groups.map(group => (
            <GroupCard
              key={group.email}
              group={group}
              onMerge={() => onSelectGroup(group)}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ── main export ────────────────────────────────────────────────────────────────
interface Props {
  open: boolean;
  onClose: () => void;
}

export function DuplicateContactsDialog({ open, onClose }: Props) {
  const [activeGroup, setActiveGroup] = useState<DuplicateGroup | null>(null);
  const { data, refetch } = useDuplicateContacts();

  const handleMerged = () => {
    setActiveGroup(null);
    refetch();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { setActiveGroup(null); onClose(); } }}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col gap-0 p-6">
        {activeGroup ? (
          <MergeView
            group={activeGroup}
            onBack={() => setActiveGroup(null)}
            onMerged={handleMerged}
          />
        ) : (
          <ListView
            onSelectGroup={setActiveGroup}
          />
        )}

        {!activeGroup && data && data.total_groups > 0 && (
          <p className="text-xs text-muted-foreground pt-2 border-t">
            Merging preserves the primary contact's field values, combines all tags,
            keeps the highest lead score, and retains the most recent activity date.
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
