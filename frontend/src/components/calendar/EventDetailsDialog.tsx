import { Link } from 'react-router-dom';
import { format, parseISO } from 'date-fns';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { SOURCE_BADGE, SOURCE_NAME, immovableReason, timeLabel } from '@/lib/calendar';
import type { CalendarEvent } from '@/types/calendar';

interface EventDetailsDialogProps {
  event: CalendarEvent | null;
  timezone: string;
  onOpenChange: (open: boolean) => void;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="m-0">{children}</dd>
    </>
  );
}

/**
 * Reads an event and hands you to the real screen.
 *
 * Nothing is edited here on purpose: a calendar that grows its own copy of
 * every form is a second place for each module's rules to drift.
 */
export function EventDetailsDialog({ event, timezone, onOpenChange }: EventDetailsDialogProps) {
  if (!event) return null;

  const day = format(parseISO(event.start.slice(0, 10)), 'EEE d MMMM yyyy');
  const time = timeLabel(event);
  const { meta } = event;

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="flex h-5 w-5 items-center justify-center rounded bg-muted text-[10px] font-semibold"
            >
              {SOURCE_BADGE[event.source]}
            </span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {SOURCE_NAME[event.source]}
            </span>
            <Badge variant="outline" className="ml-auto capitalize">
              {event.status.replace('_', ' ')}
            </Badge>
          </div>
          <DialogTitle className="pt-1 text-left">{event.title}</DialogTitle>
        </DialogHeader>

        <dl className="grid grid-cols-[88px_1fr] gap-x-3 gap-y-1.5 py-1 text-sm">
          <Row label="When">
            {time ? `${day}, ${time}` : day}
            {time && <span className="text-muted-foreground"> ({timezone})</span>}
          </Row>
          {meta.recipients !== undefined && (
            <Row label="Audience">{meta.recipients.toLocaleString()} recipients</Row>
          )}
          {meta.emails !== undefined && (
            <Row label="Volume">{meta.emails.toLocaleString()} emails due this day</Row>
          )}
          {meta.duration ? <Row label="Length">{meta.duration} minutes</Row> : null}
          {meta.priority && <Row label="Priority"><span className="capitalize">{meta.priority}</span></Row>}
          {meta.assignee && <Row label="Assignee">{meta.assignee}</Row>}
          {meta.deal && <Row label="Deal">{meta.deal}</Row>}
          {meta.value && (
            <Row label="Value">
              {meta.currency} {meta.value}
            </Row>
          )}
        </dl>

        {!event.movable && (
          <p className="rounded-md border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
            {immovableReason(event)}.
          </p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button asChild>
            <Link to={event.url}>Open {SOURCE_NAME[event.source].toLowerCase()}</Link>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
