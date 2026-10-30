import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Check, Code2, Copy, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

/**
 * The snippet a customer pastes into their own website.
 *
 * Built from the API base URL rather than from window.location: the app can be
 * reached on more than one host, and a snippet pointing at whichever one the
 * marketer happened to be using would break the day that host changes.
 */
function snippetOrigin(): string {
  const base = import.meta.env.VITE_API_URL || window.location.origin;
  try {
    return new URL(base, window.location.origin).origin;
  } catch {
    return window.location.origin;
  }
}

export const WebsiteTab = () => {
  const organization = useAuthStore((state) => state.organization);
  const [copied, setCopied] = useState(false);

  const key = organization?.tracking_key;
  const snippet = key
    ? `<script async src="${snippetOrigin()}/t.js?k=${key}"></script>`
    : '';

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard refused — the snippet is selectable on screen anyway.
    }
  };

  if (!key) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          This organization has no website key yet. Reload the page; if it
          persists, sign out and back in.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Code2 className="h-4 w-4" />
            Your website snippet
          </CardTitle>
          <CardDescription>
            Paste this once, just before the closing <code>&lt;/body&gt;</code>{' '}
            tag on every page of your site. It shows your popups.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <pre className="overflow-x-auto rounded-md border bg-muted/50 p-3 text-xs">
            <code>{snippet}</code>
          </pre>
          <Button size="sm" onClick={copy}>
            {copied ? (
              <>
                <Check className="mr-1.5 h-3.5 w-3.5" /> Copied
              </>
            ) : (
              <>
                <Copy className="mr-1.5 h-3.5 w-3.5" /> Copy snippet
              </>
            )}
          </Button>
          <p className="text-xs text-muted-foreground">
            The key identifies your account; it does not grant access to it.
            Everything the snippet can read is already public on your forms.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>What it shows</CardTitle>
          <CardDescription>
            Any form whose display type is Popup, Slide-in or Top bar, and
            whose status is Active.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            A form only appears here once it is active. Set the display type
            and the trigger in the form builder.
          </p>
          <Button asChild variant="outline" size="sm">
            <Link to="/forms">
              Go to forms <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Before you publish</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Popups collect personal data, so if your site has a cookie or
            consent banner, place the snippet behind it.
          </p>
          <p>
            Test on a staging page first. A popup set to show on every page
            with no delay is the fastest way to lose a visitor.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};
