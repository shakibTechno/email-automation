import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Search,
  MoreVertical,
  Pencil,
  Copy,
  Trash2,
  Eye,
  Pause,
  XCircle,
  Users,
  Archive,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { CampaignStatusBadge } from '@/components/campaigns/CampaignStatusBadge';
import { useCampaigns } from '@/hooks/useCampaigns';
import { CampaignStatus } from '@/types/campaign';
import { cn, debounce, formatDate, formatDateTime } from '@/lib/utils';

const statusFilters: { value: CampaignStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'draft', label: 'Draft' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'sending', label: 'Sending' },
  { value: 'sent', label: 'Sent' },
  { value: 'paused', label: 'Paused' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'archived', label: 'Archived' },
];

export const CampaignListPage = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | 'all'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [campaignToDelete, setCampaignToDelete] = useState<string | null>(null);

  const {
    campaigns,
    total,
    page,
    perPage,
    totalPages,
    isLoading,
    deleteCampaign,
    duplicateCampaign,
    pauseCampaign,
    cancelCampaign,
    archiveCampaign,
  } = useCampaigns({
    search: searchQuery || undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    page: currentPage,
    page_size: 20,
  });

  const handleSearch = debounce((value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  }, 300);

  const handleDelete = (id: string) => {
    setCampaignToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (campaignToDelete) {
      deleteCampaign(campaignToDelete);
      setDeleteDialogOpen(false);
      setCampaignToDelete(null);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Campaigns</h1>
          <p className="text-muted-foreground">
            Create and manage your email campaigns
          </p>
        </div>
        <Button onClick={() => navigate('/campaigns/new')}>
          <Plus className="h-4 w-4 mr-2" />
          Create Campaign
        </Button>
      </div>

      {/* Filters */}
      <div className="space-y-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search campaigns..."
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {statusFilters.map((sf) => (
            <button
              key={sf.value}
              onClick={() => {
                setStatusFilter(sf.value);
                setCurrentPage(1);
              }}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded-full border transition-colors',
                statusFilter === sf.value
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background text-muted-foreground border-border hover:bg-accent hover:text-accent-foreground'
              )}
            >
              {sf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : campaigns.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <div className="h-16 w-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
            <Plus className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium">No campaigns yet</h3>
          <p className="text-muted-foreground mt-1 mb-4">
            Create your first email campaign to get started
          </p>
          <Button onClick={() => navigate('/campaigns/new')}>
            <Plus className="h-4 w-4 mr-2" />
            Create Campaign
          </Button>
        </div>
      ) : (
        <>
          {/* Campaign Table */}
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    Name
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    Status
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    Subject
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Users className="h-3.5 w-3.5" />
                      Recipients
                    </div>
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    Date
                  </th>
                  <th className="text-right px-4 py-3 text-sm font-medium text-muted-foreground">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {campaigns.map((campaign) => (
                  <tr
                    key={campaign.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/campaigns/${campaign.id}`)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-sm">{campaign.name}</div>
                      {campaign.template_name && (
                        <div className="text-xs text-muted-foreground">
                          Template: {campaign.template_name}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <CampaignStatusBadge status={campaign.status} />
                        {campaign.status === 'sending' && campaign.send_progress && (
                          <div className="w-20">
                            <div className="h-1.5 w-full rounded-full bg-yellow-200 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-yellow-500 transition-all duration-500"
                                style={{ width: `${campaign.send_progress.percent}%` }}
                              />
                            </div>
                            <span className="text-[10px] text-muted-foreground">
                              {campaign.send_progress.percent}%
                            </span>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground max-w-[200px] truncate">
                      {campaign.subject || '(No subject)'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {campaign.recipient_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {campaign.sent_at
                        ? formatDateTime(campaign.sent_at)
                        : campaign.scheduled_at
                        ? formatDateTime(campaign.scheduled_at)
                        : formatDate(campaign.created_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/campaigns/${campaign.id}`);
                            }}
                          >
                            <Eye className="h-4 w-4 mr-2" /> View
                          </DropdownMenuItem>
                          {campaign.status === 'draft' && (
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/campaigns/${campaign.id}/edit`);
                              }}
                            >
                              <Pencil className="h-4 w-4 mr-2" /> Edit
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              duplicateCampaign(campaign.id);
                            }}
                          >
                            <Copy className="h-4 w-4 mr-2" /> Duplicate
                          </DropdownMenuItem>
                          {campaign.status === 'scheduled' && (
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                pauseCampaign(campaign.id);
                              }}
                            >
                              <Pause className="h-4 w-4 mr-2" /> Pause
                            </DropdownMenuItem>
                          )}
                          {(campaign.status === 'scheduled' ||
                            campaign.status === 'paused') && (
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                cancelCampaign(campaign.id);
                              }}
                            >
                              <XCircle className="h-4 w-4 mr-2" /> Cancel
                            </DropdownMenuItem>
                          )}
                          {(campaign.status === 'sent' ||
                            campaign.status === 'cancelled') && (
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                archiveCampaign(campaign.id);
                              }}
                            >
                              <Archive className="h-4 w-4 mr-2" /> Archive
                            </DropdownMenuItem>
                          )}
                          {campaign.status === 'draft' && (
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(campaign.id);
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-2" /> Delete
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Showing {(page - 1) * perPage + 1} to{' '}
                {Math.min(page * perPage, total)} of {total} campaigns
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(page - 1)}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(page + 1)}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Campaign</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this campaign? This action cannot
              be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
