import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
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
  Send,
  Archive } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
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
    <div className="w-full space-y-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Campaigns</h1>
          <p className="text-[13px] text-muted-foreground">
            One message to many people, now or scheduled.
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => navigate('/campaigns/new')}>
            <Plus className="h-3.5 w-3.5" /> New campaign
          </Button>
        </div>
      </div>

      <div className="rounded-lg border bg-card shadow-card">
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <div className="relative max-w-xs flex-1">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle-foreground" />
            <Input
              placeholder="Search campaigns…"
              onChange={(e) => handleSearch(e.target.value)}
              className="h-8 pl-8"
            />
          </div>

          <div className="flex flex-wrap gap-1">
            {statusFilters.map((sf) => (
              <button
                key={sf.value}
                type="button"
                aria-pressed={statusFilter === sf.value}
                onClick={() => {
                  setStatusFilter(sf.value);
                  setCurrentPage(1);
                }}
                className={cn(
                  'rounded-md border px-2.5 py-1 font-mono text-[11px] transition-colors',
                  statusFilter === sf.value
                    ? 'border-transparent bg-brand-fill text-brand-ink'
                    : 'border-border text-muted-foreground hover:text-foreground'
                )}
              >
                {sf.label}
              </button>
            ))}
          </div>

          <span className="ml-auto font-mono text-[11px] text-subtle-foreground">
            {new Intl.NumberFormat('en').format(total ?? 0)} shown
          </span>
        </div>

        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12 w-full rounded-md" />
            ))}
          </div>
        ) : campaigns.length === 0 ? (
          <div className="px-4 py-14 text-center">
            <Send className="mx-auto mb-3 h-6 w-6 text-subtle-foreground" />
            <h3 className="mb-1 text-[14px] font-semibold">
              {statusFilter === 'all' ? 'No campaigns yet' : `No ${statusFilter} campaigns`}
            </h3>
            <p className="mb-4 text-[12.5px] text-muted-foreground">
              {statusFilter === 'all'
                ? 'Create your first campaign to start sending.'
                : 'Try a different status filter.'}
            </p>
            {statusFilter === 'all' ? (
              <Button size="sm" onClick={() => navigate('/campaigns/new')}>
                <Plus className="h-3.5 w-3.5" /> New campaign
              </Button>
            ) : (
              <Button variant="outline" size="sm" onClick={() => setStatusFilter('all')}>
                Show all campaigns
              </Button>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-[13px]">
                <thead>
                  <tr className="border-b">
                    {['Campaign', 'Status', 'Subject', 'Recipients', 'Date', ''].map((h, i) => (
                      <th
                        key={h || i}
                        className={cn(
                          'px-3 pb-2.5 pt-3 text-left font-mono text-[9.5px] font-medium uppercase tracking-[0.13em] text-subtle-foreground',
                          h === 'Recipients' && 'text-right',
                          h === '' && 'w-10'
                        )}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {campaigns.map((campaign) => (
                    <tr
                      key={campaign.id}
                      className="border-b transition-colors last:border-b-0 hover:bg-secondary/50"
                    >
                      <td className="px-3 py-2.5">
                        {/* A real link, not a click handler on the row: that was
                            unreachable by keyboard and did not actually fire. */}
                        <Link
                          to={`/campaigns/${campaign.id}`}
                          className="font-semibold text-foreground hover:text-brand"
                        >
                          {campaign.name}
                        </Link>
                        {campaign.template_name && (
                          <div className="text-[11px] text-subtle-foreground">
                            {campaign.template_name}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex flex-col gap-1">
                          <CampaignStatusBadge status={campaign.status} />
                          {campaign.status === 'sending' && campaign.send_progress && (
                            <div className="w-20">
                              <div className="bar-track">
                                <div
                                  className="bar-fill transition-all duration-500"
                                  style={{ width: `${campaign.send_progress.percent}%` }}
                                />
                              </div>
                              <span className="font-mono text-[10px] text-subtle-foreground">
                                {campaign.send_progress.percent}%
                              </span>
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="max-w-[220px] truncate px-3 py-2.5 text-muted-foreground">
                        {campaign.subject || '(No subject)'}
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono text-[12px]">
                        {campaign.recipient_count.toLocaleString()}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-[11.5px] text-muted-foreground">
                        {campaign.sent_at
                          ? formatDateTime(campaign.sent_at)
                          : campaign.scheduled_at
                          ? formatDateTime(campaign.scheduled_at)
                          : formatDate(campaign.created_at)}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                              <MoreVertical className="h-3.5 w-3.5" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/campaigns/${campaign.id}`);
                              }}
                            >
                              <Eye className="mr-2 h-4 w-4" /> View
                            </DropdownMenuItem>
                            {campaign.status === 'draft' && (
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate(`/campaigns/${campaign.id}/edit`);
                                }}
                              >
                                <Pencil className="mr-2 h-4 w-4" /> Edit
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                duplicateCampaign(campaign.id);
                              }}
                            >
                              <Copy className="mr-2 h-4 w-4" /> Duplicate
                            </DropdownMenuItem>
                            {campaign.status === 'scheduled' && (
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation();
                                  pauseCampaign(campaign.id);
                                }}
                              >
                                <Pause className="mr-2 h-4 w-4" /> Pause
                              </DropdownMenuItem>
                            )}
                            {(campaign.status === 'scheduled' || campaign.status === 'paused') && (
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation();
                                  cancelCampaign(campaign.id);
                                }}
                              >
                                <XCircle className="mr-2 h-4 w-4" /> Cancel
                              </DropdownMenuItem>
                            )}
                            {(campaign.status === 'sent' || campaign.status === 'cancelled') && (
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation();
                                  archiveCampaign(campaign.id);
                                }}
                              >
                                <Archive className="mr-2 h-4 w-4" /> Archive
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
                                <Trash2 className="mr-2 h-4 w-4" /> Delete
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

            {totalPages > 1 && (
              <div className="flex flex-wrap items-center justify-between gap-2 border-t px-3 py-2.5">
                <span className="font-mono text-[11px] text-subtle-foreground">
                  {(page - 1) * perPage + 1}–{Math.min(page * perPage, total)} of {total}
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8"
                    onClick={() => setCurrentPage(page - 1)}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  <span className="px-2 font-mono text-[11px] text-muted-foreground">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8"
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
      </div>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete campaign</DialogTitle>
            <DialogDescription>
              This removes the campaign and its draft content. It cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
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
