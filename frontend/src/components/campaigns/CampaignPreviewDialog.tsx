import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { campaignsApi } from '@/api/campaigns';

interface CampaignPreviewDialogProps {
  campaignId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const CampaignPreviewDialog = ({
  campaignId,
  open,
  onOpenChange,
}: CampaignPreviewDialogProps) => {
  const [html, setHtml] = useState('');
  const [subject, setSubject] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && campaignId) {
      setLoading(true);
      campaignsApi
        .previewCampaign(campaignId)
        .then((data) => {
          setHtml(data.html);
          setSubject(data.subject);
        })
        .catch(() => {
          setHtml('<p>Failed to load preview.</p>');
        })
        .finally(() => setLoading(false));
    }
  }, [open, campaignId]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {subject ? `Preview: ${subject}` : 'Campaign Preview'}
          </DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-auto border rounded bg-card min-h-[400px]">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : (
            <iframe
              srcDoc={html}
              title="Campaign Preview"
              className="w-full h-full min-h-[400px] border-0"
              sandbox="allow-same-origin"
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
