import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

/**
 * Webhook Received: another system starts this workflow.
 *
 * The settings are two plain fields, so this panel exists for the URL. The
 * trigger is unusable without it, and it only exists once the workflow has
 * been saved — the token is minted by the server.
 */

interface Props {
  config: {
    match_by?: 'email' | 'external_id';
    create_missing?: boolean;
  };
  label: string;
  webhookToken?: string;
  onChange: (config: Record<string, unknown>) => void;
  onLabelChange: (label: string) => void;
}

export default function WebhookTriggerConfigPanel({
  config, label, webhookToken, onChange, onLabelChange,
}: Props) {
  const [copied, setCopied] = useState(false);
  const matchBy = config.match_by || 'email';

  const url = webhookToken
    ? `${window.location.origin}/webhooks/workflow/${webhookToken}`
    : '';

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be refused; the box is selectable either way.
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <Label>Step label</Label>
        <Input
          className="mt-1"
          value={label || ''}
          onChange={(event) => onLabelChange(event.target.value)}
          placeholder="Order placed"
        />
      </div>

      <div>
        <Label>Post to this URL</Label>
        {url ? (
          <>
            <div className="mt-1 flex gap-2">
              <Input readOnly value={url} className="font-mono text-xs" />
              <Button
                variant="outline"
                size="icon"
                className="shrink-0"
                onClick={copy}
                title="Copy"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-success" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Anyone holding this URL can start the workflow, so treat it like
              a password. It only works while the workflow is active.
            </p>
          </>
        ) : (
          <p className="mt-1 rounded-md border border-dashed p-3 text-xs text-muted-foreground">
            Save the workflow and the URL will appear here.
          </p>
        )}
      </div>

      <div>
        <Label>Find the contact by</Label>
        <Select
          value={matchBy}
          onValueChange={(value) => onChange({ ...config, match_by: value })}
        >
          <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="email">Email address</SelectItem>
            <SelectItem value="external_id">External ID</SelectItem>
          </SelectContent>
        </Select>
        <p className="mt-1 text-xs text-muted-foreground">
          Send <code className="font-mono">{`{"${matchBy}": "…"}`}</code> in the
          body. Only contacts in this account are matched.
        </p>
      </div>

      <div className="flex items-start space-x-2">
        <Checkbox
          id="create-missing"
          checked={Boolean(config.create_missing)}
          onCheckedChange={(checked) =>
            onChange({ ...config, create_missing: Boolean(checked) })
          }
        />
        <div>
          <Label htmlFor="create-missing">
            Create the contact if we have not seen them
          </Label>
          <p className="text-xs text-muted-foreground">
            {matchBy === 'email'
              ? 'A first_name and last_name in the body are used if present.'
              : 'Only works when matching by email — a contact with no address '
                + 'cannot be reached, so an external ID alone creates nothing.'}
          </p>
        </div>
      </div>
    </div>
  );
}
