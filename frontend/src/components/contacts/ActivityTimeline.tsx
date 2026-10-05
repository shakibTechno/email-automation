import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Mail,
  MailOpen,
  MousePointer,
  UserMinus,
  FileText,
  GitBranch,
  Tag,
  ChevronDown,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { useContactActivityTimeline } from '@/hooks/useSequences';
import { formatDistanceToNow, parseISO } from 'date-fns';
import type { ActivityEvent } from '@/types/sequence';

const EVENT_ICONS: Record<string, React.ReactNode> = {
  email_sent: <Mail className="h-4 w-4 text-brand" />,
  email_opened: <MailOpen className="h-4 w-4 text-success" />,
  email_clicked: <MousePointer className="h-4 w-4 text-info" />,
  unsubscribed: <UserMinus className="h-4 w-4 text-destructive" />,
  form_submission: <FileText className="h-4 w-4 text-warning" />,
  workflow_active: <GitBranch className="h-4 w-4 text-info" />,
  workflow_completed: <GitBranch className="h-4 w-4 text-success" />,
  workflow_failed: <GitBranch className="h-4 w-4 text-destructive" />,
  workflow_cancelled: <GitBranch className="h-4 w-4 text-subtle-foreground" />,
  sequence_email_sent: <Clock className="h-4 w-4 text-brand" />,
  tag_added: <Tag className="h-4 w-4 text-success" />,
};

const EVENT_COLORS: Record<string, string> = {
  email_sent: 'bg-info/[.10] border-info/[.20]',
  email_opened: 'bg-success/[.10] border-success/[.20]',
  email_clicked: 'bg-info/[.10] border-info/[.20]',
  unsubscribed: 'bg-destructive/[.10] border-destructive/[.20]',
  form_submission: 'bg-warning/[.10] border-warning/[.20]',
  workflow_completed: 'bg-success/[.10] border-success/[.20]',
  workflow_failed: 'bg-destructive/[.10] border-destructive/[.20]',
  sequence_email_sent: 'bg-info/[.10] border-info/[.20]',
  tag_added: 'bg-success/[.10] border-success/[.20]',
};

function getIcon(type: string) {
  return EVENT_ICONS[type] || <AlertCircle className="h-4 w-4 text-subtle-foreground" />;
}

function getColor(type: string) {
  return EVENT_COLORS[type] || 'bg-secondary/50 border-border';
}

function EventItem({ event }: { event: ActivityEvent }) {
  const [expanded, setExpanded] = useState(false);
  const hasDescription = !!event.description;
  const hasMeta = Object.values(event.meta).some(Boolean);

  return (
    <div className={`flex gap-3 p-3 rounded-lg border ${getColor(event.type)}`}>
      <div className="flex-shrink-0 mt-0.5">{getIcon(event.type)}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium text-foreground leading-snug">{event.title}</p>
          <span className="text-xs text-subtle-foreground flex-shrink-0 mt-0.5">
            {formatDistanceToNow(parseISO(event.timestamp), { addSuffix: true })}
          </span>
        </div>
        {hasDescription && (
          <p className="text-xs text-muted-foreground mt-0.5 truncate">{event.description}</p>
        )}
        {hasMeta && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-brand hover:text-brand mt-1 flex items-center gap-1"
          >
            Details
            <ChevronDown className={`h-3 w-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </button>
        )}
        {expanded && hasMeta && (
          <div className="mt-2 text-xs text-muted-foreground space-y-0.5">
            {Object.entries(event.meta).filter(([, v]) => v).map(([k, v]) => (
              <div key={k}>
                <span className="font-medium">{k}:</span> {String(v)}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface Props {
  contactId: string;
}

export default function ActivityTimeline({ contactId }: Props) {
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const { data, isLoading, isFetching } = useContactActivityTimeline(contactId, { limit, offset });

  const events = data?.events || [];
  const total = data?.total || 0;
  const hasMore = offset + limit < total;
  const hasPrev = offset > 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">
          Activity ({total} events)
        </h3>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-subtle-foreground text-sm">Loading timeline...</div>
      ) : events.length === 0 ? (
        <div className="text-center py-10 border-2 border-dashed rounded-lg">
          <Clock className="h-8 w-8 mx-auto text-subtle-foreground mb-2" />
          <p className="text-sm text-subtle-foreground">No activity recorded yet</p>
        </div>
      ) : (
        <>
          <div className="space-y-2">
            {events.map((event, idx) => (
              <EventItem key={`${event.type}-${event.timestamp}-${idx}`} event={event} />
            ))}
          </div>

          <div className="flex items-center justify-between pt-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!hasPrev || isFetching}
              onClick={() => setOffset(Math.max(0, offset - limit))}
            >
              Previous
            </Button>
            <span className="text-xs text-muted-foreground">
              {offset + 1}–{Math.min(offset + limit, total)} of {total}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasMore || isFetching}
              onClick={() => setOffset(offset + limit)}
            >
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
