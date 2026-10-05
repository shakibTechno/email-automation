import { useState, useEffect } from 'react';
import { Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { formsApi } from '@/api/forms';
import { toast } from 'sonner';

interface EmbedCodeDialogProps {
  formId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const EmbedCodeDialog = ({
  formId,
  open,
  onOpenChange,
}: EmbedCodeDialogProps) => {
  const [embedData, setEmbedData] = useState<{
    embed_html: string;
    iframe_code: string;
    form_url: string;
  } | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  useEffect(() => {
    if (open && formId) {
      formsApi.getEmbedCode(formId).then(setEmbedData).catch(() => {
        toast.error('Failed to load embed code');
      });
    }
  }, [open, formId]);

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    toast.success('Copied to clipboard!');
    setTimeout(() => setCopiedField(null), 2000);
  };

  const CopyButton = ({ text, field }: { text: string; field: string }) => (
    <Button
      variant="outline"
      size="sm"
      onClick={() => copyToClipboard(text, field)}
    >
      {copiedField === field ? (
        <Check className="h-4 w-4 mr-1" />
      ) : (
        <Copy className="h-4 w-4 mr-1" />
      )}
      {copiedField === field ? 'Copied' : 'Copy'}
    </Button>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Embed & Share</DialogTitle>
        </DialogHeader>
        {embedData ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Direct Link</Label>
                <CopyButton text={embedData.form_url} field="url" />
              </div>
              <Input value={embedData.form_url} readOnly />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>iFrame Embed</Label>
                <CopyButton text={embedData.iframe_code} field="iframe" />
              </div>
              <Textarea
                value={embedData.iframe_code}
                readOnly
                rows={3}
                className="font-mono text-xs"
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>JavaScript Embed</Label>
                <CopyButton text={embedData.embed_html} field="js" />
              </div>
              <Textarea
                value={embedData.embed_html}
                readOnly
                rows={3}
                className="font-mono text-xs"
              />
            </div>
          </div>
        ) : (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
