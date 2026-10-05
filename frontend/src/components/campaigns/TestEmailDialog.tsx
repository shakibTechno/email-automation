import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { X } from 'lucide-react';

interface TestEmailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSend: (emails: string[]) => Promise<void>;
  isSending: boolean;
}

export const TestEmailDialog = ({
  open,
  onOpenChange,
  onSend,
  isSending,
}: TestEmailDialogProps) => {
  const [emailInput, setEmailInput] = useState('');
  const [emails, setEmails] = useState<string[]>([]);
  const [error, setError] = useState('');

  const addEmail = () => {
    const trimmed = emailInput.trim();
    if (!trimmed) return;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmed)) {
      setError('Please enter a valid email address.');
      return;
    }
    if (emails.includes(trimmed)) {
      setError('This email is already added.');
      return;
    }
    if (emails.length >= 5) {
      setError('Maximum 5 test emails allowed.');
      return;
    }

    setEmails([...emails, trimmed]);
    setEmailInput('');
    setError('');
  };

  const removeEmail = (email: string) => {
    setEmails(emails.filter((e) => e !== email));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addEmail();
    }
  };

  const handleSend = async () => {
    if (emails.length === 0) {
      setError('Add at least one email address.');
      return;
    }
    await onSend(emails);
    setEmails([]);
    setEmailInput('');
    setError('');
    onOpenChange(false);
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setEmails([]);
      setEmailInput('');
      setError('');
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send Test Email</DialogTitle>
          <DialogDescription>
            Send a preview of this campaign to up to 5 email addresses.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="test-email">Email Address</Label>
            <div className="flex gap-2">
              <Input
                id="test-email"
                type="email"
                placeholder="name@example.com"
                value={emailInput}
                onChange={(e) => {
                  setEmailInput(e.target.value);
                  setError('');
                }}
                onKeyDown={handleKeyDown}
              />
              <Button type="button" variant="outline" onClick={addEmail}>
                Add
              </Button>
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>
          {emails.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {emails.map((email) => (
                <span
                  key={email}
                  className="inline-flex items-center gap-1 px-2 py-1 text-sm bg-secondary rounded-md"
                >
                  {email}
                  <button
                    type="button"
                    onClick={() => removeEmail(email)}
                    className="hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSend}
            disabled={emails.length === 0 || isSending}
          >
            {isSending ? 'Sending...' : `Send Test (${emails.length})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
