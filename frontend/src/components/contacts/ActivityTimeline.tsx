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
  email_sent: <Mail className="h-4 w-4 text-blue-500" />,
  email_opened: <MailOpen className="h-4 w-4 text-green-500" />,
  email_clicked: <MousePointer className="h-4 w-4 text-purple-500" />,
  unsubscribed: <UserMinus className="h-4 w-4 text-red-500" />,
  form_submission: <FileText className="h-4 w-4 text-orange-500" />,
  workflow_active: <GitBranch className="h-4 w-4 text-blue-400" />,
  workflow_completed: <GitBranch className="h-4 w-4 text-green-500" />,
  workflow_failed: <GitBranch className="h-4 w-4 text-red-400" />,
  workflow_cancelled: <GitBranch className="h-4 w-4 text-gray-400" />,
  sequence_email_sent: <Clock className="h-4 w-4 text-indigo-500" />,
  tag_added: <Tag className="h-4 w-4 text-teal-500" />,
};

const EVENT_COLORS: Record<string, string> = {
  email_sent: 'bg-blue-50 border-blue-100',
  email_opened: 'bg-green-50 border-green-100',
  email_clicked: 'bg-purple-50 border-purple-100',
  unsubscribed: 'bg-red-50 border-red-100',
  form_submission: 'bg-orange-50 border-orange-100',
  workflow_completed: 'bg-green-50 border-green-100',
  workflow_failed: 'bg-red-50 border-red-100',
  sequence_email_sent: 'bg-indigo-50 border-indigo-100',
  tag_added: 'bg-teal-50 border-teal-100',
};

function getIcon(type: string) {
  return EVENT_ICONS[type] || <AlertCircle className="h-4 w-4 text-gray-400" />;
}

function getColor(type: string) {
  return EVENT_COLORS[type] || 'bg-gray-50 border-gray-100';
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
          <p className="text-sm font-medium text-gray-900 leading-snug">{event.title}</p>
          <span className="text-xs text-gray-400 flex-shrink-0 mt-0.5">
            {formatDistanceToNow(parseISO(event.timestamp), { addSuffix: true })}
          </span>
        </div>
        {hasDescription && (
          <p className="text-xs text-gray-500 mt-0.5 truncate">{event.description}</p>
        )}
        {hasMeta && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-blue-500 hover:text-blue-700 mt-1 flex items-center gap-1"
          >
            Details
            <ChevronDown className={`h-3 w-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </button>
        )}
        {expanded && hasMeta && (
          <div className="mt-2 text-xs text-gray-500 space-y-0.5">
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
        <h3 className="text-sm font-semibold text-gray-700">
          Activity ({total} events)
        </h3>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-400 text-sm">Loading timeline...</div>
      ) : events.length === 0 ? (
        <div className="text-center py-10 border-2 border-dashed rounded-lg">
          <Clock className="h-8 w-8 mx-auto text-gray-300 mb-2" />
          <p className="text-sm text-gray-400">No activity recorded yet</p>
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
            <span className="text-xs text-gray-500">
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
