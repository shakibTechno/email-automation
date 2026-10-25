import { useEffect, useState } from 'react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useTenantActions } from '@/hooks/useLandlord';

export type SuspensionAction =
  | 'suspend_sending'
  | 'resume_sending'
  | 'suspend_account'
  | 'restore_account';

interface SuspensionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  action: SuspensionAction;
  tenantId: string;
  tenantName: string;
  /** True when sending was paused independently of the account suspension. */
  sendingPaused?: boolean;
}

const COPY: Record<
  SuspensionAction,
  { title: string; body: string; confirm: string; destructive: boolean; needsReason: boolean }
> = {
  suspend_sending: {
    title: 'Suspend sending',
    body:
      'Campaigns, sequences and workflows will refuse to send, and the mail server tenant is suspended. The customer keeps full access to the app and can see their data.',
    confirm: 'Suspend sending',
    destructive: true,
    needsReason: true,
  },
  resume_sending: {
    title: 'Resume sending',
    body:
      'Sending is re-enabled immediately, including any pause the automatic bounce guardrails applied. Check the bounce rate first — resuming a tenant that is still bouncing puts the shared IP back at risk.',
    confirm: 'Resume sending',
    destructive: false,
    needsReason: false,
  },
  suspend_account: {
    title: 'Suspend account',
    body:
      'Everyone in this organization is signed out and refused at login, and the API rejects tokens already issued. Sending stops too. Nothing is deleted.',
    confirm: 'Suspend account',
    destructive: true,
    needsReason: true,
  },
  restore_account: {
    title: 'Restore account',
    body: 'The organization can sign in and use the app again.',
    confirm: 'Restore account',
    destructive: false,
    needsReason: false,
  },
};

/**
 * One dialog for all four suspension transitions.
 *
 * The reason is mandatory on both suspend paths and not a formality: it is the
 * only thing the tenant-facing message and the activity log have to explain
 * what happened, and a suspension nobody can account for later is worse than
 * none.
 */
export const SuspensionDialog = ({
  open,
  onOpenChange,
  action,
  tenantId,
  tenantName,
  sendingPaused = false,
}: SuspensionDialogProps) => {
  const copy = COPY[action];
  const [reason, setReason] = useState('');
  const [alsoResumeSending, setAlsoResumeSending] = useState(true);
  const { suspendSending, resumeSending, suspendAccount, restoreAccount, isBusy } =
    useTenantActions(tenantId);

  useEffect(() => {
    if (open) {
      setReason('');
      // A tenant whose sending was paused by the guardrails should not have
      // that pause lifted silently just because the account came back.
      setAlsoResumeSending(!sendingPaused);
    }
  }, [open, sendingPaused]);

  const close = () => onOpenChange(false);
  const done = { onSuccess: close };

  const submit = () => {
    switch (action) {
      case 'suspend_sending':
        return suspendSending.mutate(reason.trim(), done);
      case 'resume_sending':
        return resumeSending.mutate(undefined, done);
      case 'suspend_account':
        return suspendAccount.mutate(reason.trim(), done);
      case 'restore_account':
        return restoreAccount.mutate(alsoResumeSending, done);
    }
  };

  const blocked = copy.needsReason && reason.trim().length < 3;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[15px]">
            {copy.title} — {tenantName}
          </DialogTitle>
          <DialogDescription className="text-[12.5px]">{copy.body}</DialogDescription>
        </DialogHeader>

        {copy.needsReason && (
          <div className="space-y-1.5">
            <Label htmlFor="suspension-reason" className="text-[12.5px]">
              Reason
            </Label>
            <Textarea
              id="suspension-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. 14% bounce rate on a purchased list"
              className="min-h-[72px] text-[13px]"
            />
            <p className="text-[11.5px] text-muted-foreground">
              Recorded in the activity log and shown to the customer.
            </p>
          </div>
        )}

        {action === 'restore_account' && sendingPaused && (
          <label className="flex items-start gap-2 rounded-md border bg-muted/40 p-2.5 text-[12.5px]">
            <Checkbox
              checked={alsoResumeSending}
              onCheckedChange={(v) => setAlsoResumeSending(v === true)}
              className="mt-0.5"
            />
            <span>
              Resume sending as well
              <span className="block text-[11.5px] text-muted-foreground">
                Sending is separately paused for this tenant. Leave this unchecked to restore
                access without letting them mail again.
              </span>
            </span>
          </label>
        )}

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={close} disabled={isBusy}>
            Cancel
          </Button>
          <Button
            size="sm"
            variant={copy.destructive ? 'destructive' : 'default'}
            onClick={submit}
            disabled={isBusy || blocked}
          >
            {isBusy ? 'Working…' : copy.confirm}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
