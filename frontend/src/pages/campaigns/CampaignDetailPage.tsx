import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Pencil,
  Copy,
  Trash2,
  Pause,
  XCircle,
  Eye,
  Send,
  Users,
  Mail,
  Clock,
  User,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { CampaignStatusBadge } from '@/components/campaigns/CampaignStatusBadge';
import { CampaignPreviewDialog } from '@/components/campaigns/CampaignPreviewDialog';
import { TestEmailDialog } from '@/components/campaigns/TestEmailDialog';
import { ABTestPanel } from '@/components/campaigns/ABTestPanel';
import { useCampaign, useCampaigns } from '@/hooks/useCampaigns';
import { useCampaignRecipients } from '@/hooks/useCampaignRecipients';
import { formatDate, formatDateTime } from '@/lib/utils';

export const CampaignDetailPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const { campaign, isLoading } = useCampaign(id || '');
  const {
    deleteCampaign,
    duplicateCampaign,
    pauseCampaign,
    cancelCampaign,
    sendTestEmail,
    isSendingTest,
  } = useCampaigns();
  const { recipients, total: recipientTotal } = useCampaignRecipients(
    id || '',
    undefined,
    campaign?.status === 'sending'
  );

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [testEmailOpen, setTestEmailOpen] = useState(false);

  const handleDelete = () => {
    if (id) {
      deleteCampaign(id);
      navigate('/campaigns');
    }
  };

  const handleTestEmail = async (emails: string[]) => {
    if (id) {
      await sendTestEmail(id, { test_emails: emails });
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">Campaign not found.</p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => navigate('/campaigns')}
        >
          Back to Campaigns
        </Button>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/campaigns')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{campaign.name}</h1>
              <CampaignStatusBadge status={campaign.status} />
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Created {formatDate(campaign.created_at)}
              {campaign.created_by_name && ` by ${campaign.created_by_name}`}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setPreviewOpen(true)}>
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setTestEmailOpen(true)}
          >
            <Send className="h-4 w-4 mr-2" />
            Test
          </Button>
          {campaign.status === 'draft' && (
            <Button
              size="sm"
              onClick={() => navigate(`/campaigns/${id}/edit`)}
            >
              <Pencil className="h-4 w-4 mr-2" />
              Edit
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => id && duplicateCampaign(id)}
          >
            <Copy className="h-4 w-4 mr-2" />
            Duplicate
          </Button>
          {campaign.status === 'scheduled' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => id && pauseCampaign(id)}
            >
              <Pause className="h-4 w-4 mr-2" />
              Pause
            </Button>
          )}
          {(campaign.status === 'scheduled' || campaign.status === 'paused') && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => id && cancelCampaign(id)}
            >
              <XCircle className="h-4 w-4 mr-2" />
              Cancel
            </Button>
          )}
          {campaign.status === 'draft' && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Sending Progress Banner */}
      {campaign.status === 'sending' && (
        <Card className="p-5 border-warning/[.30] bg-warning/[.10]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-warning font-semibold">
              <Loader2 className="h-4 w-4 animate-spin" />
              Sending in progress…
            </div>
            {campaign.send_progress && (
              <span className="text-sm text-warning font-medium">
                {campaign.send_progress.sent.toLocaleString()} /{' '}
                {campaign.send_progress.total.toLocaleString()} sent
                ({campaign.send_progress.percent}%)
              </span>
            )}
          </div>
          <div className="h-2 w-full rounded-full bg-warning/[.20] overflow-hidden">
            <div
              className="h-full rounded-full bg-warning transition-all duration-500"
              style={{ width: `${campaign.send_progress?.percent ?? 0}%` }}
            />
          </div>
        </Card>
      )}

      {/* Campaign Details */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="p-5 space-y-4">
          <h2 className="font-semibold flex items-center gap-2">
            <Mail className="h-4 w-4" /> Email Settings
          </h2>
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground">Subject:</span>{' '}
              <span className="font-medium">{campaign.subject || '(Not set)'}</span>
            </div>
            {campaign.preheader_text && (
              <div>
                <span className="text-muted-foreground">Preheader:</span>{' '}
                {campaign.preheader_text}
              </div>
            )}
            <div>
              <span className="text-muted-foreground">Template:</span>{' '}
              {campaign.template_name ? (
                <span className="font-medium">{campaign.template_name}</span>
              ) : (
                '(No template)'
              )}
            </div>
          </div>
        </Card>

        <Card className="p-5 space-y-4">
          <h2 className="font-semibold flex items-center gap-2">
            <User className="h-4 w-4" /> Sender
          </h2>
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground">From:</span>{' '}
              {campaign.sender_name && campaign.sender_email
                ? `${campaign.sender_name} <${campaign.sender_email}>`
                : '(Not set)'}
            </div>
            {campaign.reply_to_email && (
              <div>
                <span className="text-muted-foreground">Reply-To:</span>{' '}
                {campaign.reply_to_email}
              </div>
            )}
          </div>
        </Card>

        <Card className="p-5 space-y-4">
          <h2 className="font-semibold flex items-center gap-2">
            <Users className="h-4 w-4" /> Recipients
          </h2>
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground">Type:</span>{' '}
              {campaign.recipient_type === 'all_subscribed'
                ? 'All subscribed contacts'
                : 'Contacts by tags'}
            </div>
            {campaign.recipient_tags_detail &&
              campaign.recipient_tags_detail.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {campaign.recipient_tags_detail.map((tag) => (
                    <Badge key={tag.id} variant="outline" className="text-xs">
                      {tag.name}
                    </Badge>
                  ))}
                </div>
              )}
            <div>
              <span className="text-muted-foreground">Count:</span>{' '}
              <span className="font-medium">
                {campaign.recipient_count.toLocaleString()}
              </span>
            </div>
          </div>
        </Card>

        <Card className="p-5 space-y-4">
          <h2 className="font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4" /> Timeline
          </h2>
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground">Created:</span>{' '}
              {formatDateTime(campaign.created_at)}
            </div>
            {campaign.scheduled_at && (
              <div>
                <span className="text-muted-foreground">Scheduled:</span>{' '}
                {formatDateTime(campaign.scheduled_at)}
              </div>
            )}
            {campaign.sent_at && (
              <div>
                <span className="text-muted-foreground">Sent:</span>{' '}
                {formatDateTime(campaign.sent_at)}
              </div>
            )}
            {campaign.completed_at && (
              <div>
                <span className="text-muted-foreground">Completed:</span>{' '}
                {formatDateTime(campaign.completed_at)}
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* A/B Test Panel */}
      {campaign.ab_test && campaign.ab_test.status !== 'draft' && (
        <ABTestPanel campaignId={id || ''} abTest={campaign.ab_test} />
      )}

      {/* Recipients Table */}
      {recipients.length > 0 && (
        <Card className="p-5 space-y-4">
          <h2 className="font-semibold flex items-center gap-2">
            <Users className="h-4 w-4" /> Recipient Details ({recipientTotal})
          </h2>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-secondary/50 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">
                    Email
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">
                    Name
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">
                    Status
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">
                    Sent
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">
                    Opened
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {recipients.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-2">{r.email}</td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {r.contact_name || '-'}
                    </td>
                    <td className="px-4 py-2">
                      <Badge variant="outline" className="text-xs">
                        {r.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {r.sent_at ? formatDateTime(r.sent_at) : '-'}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {r.opened_at ? formatDateTime(r.opened_at) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Campaign</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{campaign.name}"? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Preview & Test Dialogs */}
      <CampaignPreviewDialog
        campaignId={id || null}
        open={previewOpen}
        onOpenChange={setPreviewOpen}
      />
      <TestEmailDialog
        open={testEmailOpen}
        onOpenChange={setTestEmailOpen}
        onSend={handleTestEmail}
        isSending={isSendingTest}
      />
    </div>
  );
};
