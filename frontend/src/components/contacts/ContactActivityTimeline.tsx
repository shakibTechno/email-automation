import { useContactTimeline } from '@/hooks/useContactTimeline';
import { TimelineEvent } from '@/types/contact';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime } from '@/lib/utils';
import {
  Mail,
  MailOpen,
  MousePointerClick,
  AlertCircle,
  UserMinus,
  FileText,
  GitBranch,
  CheckCircle2,
  TrendingUp,
  Phone,
  MessageSquare,
  Calendar,
  ClipboardList,
  StickyNote,
} from 'lucide-react';

interface Props {
  contactId: string;
}

const EVENT_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  email_sent:          { icon: Mail,               color: 'text-blue-500',   label: 'Email Sent' },
  email_opened:        { icon: MailOpen,            color: 'text-green-500',  label: 'Email Opened' },
  email_clicked:       { icon: MousePointerClick,   color: 'text-purple-500', label: 'Link Clicked' },
  email_bounced:       { icon: AlertCircle,         color: 'text-red-500',    label: 'Email Bounced' },
  email_unsubscribed:  { icon: UserMinus,           color: 'text-orange-500', label: 'Unsubscribed' },
  form_submission:     { icon: FileText,            color: 'text-teal-500',   label: 'Form Submitted' },
  workflow_started:    { icon: GitBranch,           color: 'text-indigo-500', label: 'Workflow Started' },
  workflow_completed:  { icon: CheckCircle2,        color: 'text-emerald-500',label: 'Workflow Completed' },
  score_change:        { icon: TrendingUp,          color: 'text-amber-500',  label: 'Score Changed' },
  crm_call:            { icon: Phone,               color: 'text-sky-500',    label: 'Call' },
  crm_email:           { icon: Mail,                color: 'text-blue-400',   label: 'Email' },
  crm_meeting:         { icon: Calendar,            color: 'text-violet-500', label: 'Meeting' },
  crm_task:            { icon: ClipboardList,       color: 'text-rose-500',   label: 'Task' },
  crm_note:            { icon: StickyNote,          color: 'text-yellow-500', label: 'Note' },
  crm_message:         { icon: MessageSquare,       color: 'text-cyan-500',   label: 'Message' },
};

function getConfig(type: string) {
  return EVENT_CONFIG[type] ?? { icon: Calendar, color: 'text-gray-400', label: type };
}

function EventRow({ event }: { event: TimelineEvent }) {
  const { icon: Icon, color, label } = getConfig(event.type);

  const extra = (() => {
    if (event.type === 'score_change') {
      const { points_delta, score_before, score_after } = event.metadata;
      const sign = points_delta >= 0 ? '+' : '';
      return `${sign}${points_delta} pts  (${score_before} → ${score_after})`;
    }
    return null;
  })();

  return (
    <div className="flex gap-3 py-3 border-b last:border-0">
      <div className={`mt-0.5 flex-shrink-0 ${color}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {label}
            </span>
            <div className="text-sm font-medium truncate">{event.title}</div>
            {event.description && (
              <div className="text-xs text-muted-foreground">{event.description}</div>
            )}
            {extra && (
              <div className="text-xs font-mono text-muted-foreground mt-0.5">{extra}</div>
            )}
          </div>
          {event.timestamp && (
            <div className="text-xs text-muted-foreground flex-shrink-0 pt-0.5">
              {formatDateTime(event.timestamp)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ContactActivityTimeline({ contactId }: Props) {
  const { events, total, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } =
    useContactTimeline(contactId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="h-4 w-4 mt-0.5 rounded-full" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-4 w-48" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-2">
        No activity recorded yet.
      </div>
    );
  }

  return (
    <div>
      <div className="text-xs text-muted-foreground mb-2">{total} total events</div>
      <div>
        {events.map((event) => (
          <EventRow key={event.id} event={event} />
        ))}
      </div>
      {hasNextPage && (
        <Button
          variant="ghost"
          size="sm"
          className="mt-2 w-full"
          onClick={() => fetchNextPage()}
          disabled={isFetchingNextPage}
        >
          {isFetchingNextPage ? 'Loading…' : 'Load more'}
        </Button>
      )}
    </div>
  );
}
