import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Search, MoreVertical, Pencil, Copy, Trash2, Play, Pause, Eye,
  MousePointerClick,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { debounce } from '@/lib/utils';
import { usePopups } from '@/hooks/usePopups';
import { PopupStatusBadge } from '@/components/popups/PopupStatusBadge';
import { PopupTemplateDialog } from '@/components/popups/PopupTemplateDialog';
import { popupTypeLabels, PopupStatus } from '@/types/popup';

const statusFilters: { value: PopupStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'published', label: 'Published' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'draft', label: 'Draft' },
  { value: 'paused', label: 'Paused' },
];

export const PopupListPage = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<PopupStatus | 'all'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [templateOpen, setTemplateOpen] = useState(false);
  const [toDelete, setToDelete] = useState<string | null>(null);

  const {
    popups, total, page, perPage, totalPages, isLoading,
    deletePopup, duplicatePopup, publishPopup, pausePopup,
  } = usePopups({
    search: searchQuery || undefined,
    status: statusFilter === 'all' ? undefined : statusFilter,
    page: currentPage,
    page_size: 20,
  });

  const handleSearch = debounce((value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  }, 300);

  // An empty list after filtering is a different message from an empty
  // account, and offering "create your first pop-up" to someone who has ten
  // of them reads as broken.
  const isFiltered = Boolean(searchQuery) || statusFilter !== 'all';

  return (
    <div className="w-full space-y-3.5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Pop-ups</h1>
          <p className="text-[13px] text-muted-foreground">
            Shown on your own site through the website snippet.
          </p>
        </div>
        <Button size="sm" onClick={() => setTemplateOpen(true)}>
          <Plus className="h-3.5 w-3.5" /> New pop-up
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search pop-ups..."
            className="pl-9"
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-1.5">
          {statusFilters.map((filter) => (
            <button
              key={filter.value}
              onClick={() => { setStatusFilter(filter.value); setCurrentPage(1); }}
              aria-pressed={statusFilter === filter.value}
              className={`rounded-md border px-2.5 py-1 text-[13px] transition-colors ${
                statusFilter === filter.value
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'hover:bg-secondary'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
        </div>
      ) : popups.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-lg border bg-card">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-secondary">
            <MousePointerClick className="h-7 w-7 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-medium">
            {isFiltered ? 'Nothing matches those filters' : 'No pop-ups yet'}
          </h3>
          <p className="max-w-sm text-center text-[13px] text-muted-foreground">
            {isFiltered
              ? 'Try a different status or clear the search.'
              : 'Capture an email, offer a discount, or announce something — shown on your own website.'}
          </p>
          {isFiltered ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => { setStatusFilter('all'); setSearchQuery(''); }}
            >
              Clear filters
            </Button>
          ) : (
            <Button size="sm" onClick={() => setTemplateOpen(true)}>
              <Plus className="h-3.5 w-3.5" /> New pop-up
            </Button>
          )}
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border bg-card shadow-card">
          <table className="w-full">
            <thead className="border-b bg-secondary/50">
              <tr className="text-left text-[13px] text-muted-foreground">
                <th className="w-full px-4 py-2.5 font-medium">Name</th>
                <th className="whitespace-nowrap px-3 py-2.5 font-medium">Status</th>
                <th className="whitespace-nowrap px-3 py-2.5 font-medium">Type</th>
                <th className="whitespace-nowrap px-3 py-2.5 font-medium">Views</th>
                <th className="whitespace-nowrap px-3 py-2.5 font-medium">Conversions</th>
                <th className="px-3 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {popups.map((popup) => (
                <tr
                  key={popup.id}
                  className="cursor-pointer hover:bg-secondary/50"
                  onClick={() => navigate(`/popups/${popup.id}/edit`)}
                >
                  <td className="px-4 py-2.5">
                    <div className="font-medium">{popup.name}</div>
                    {popup.title && (
                      <div className="truncate text-[13px] text-muted-foreground">
                        {popup.title}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2.5">
                    <PopupStatusBadge status={popup.status} isLive={popup.is_live} />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-[13px]">
                    {popupTypeLabels[popup.popup_type]}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-[13px]">
                    {popup.impression_count.toLocaleString()}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-[13px]">
                    {/* The rate is meaningless without the count beside it --
                        60% of five views is not a result. */}
                    {popup.impression_count > 0 ? (
                      <>
                        {(popup.form
                          ? popup.conversion_count
                          : popup.click_count
                        ).toLocaleString()}{' '}
                        <span className="text-muted-foreground">
                          ({popup.conversion_rate}%)
                        </span>
                      </>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-7 w-7">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/popups/${popup.id}/edit`);
                          }}
                        >
                          <Pencil className="mr-2 h-4 w-4" /> Edit
                        </DropdownMenuItem>
                        {popup.status === 'published' || popup.status === 'scheduled' ? (
                          <DropdownMenuItem
                            onClick={(e) => { e.stopPropagation(); pausePopup(popup.id); }}
                          >
                            <Pause className="mr-2 h-4 w-4" /> Pause
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem
                            onClick={(e) => { e.stopPropagation(); publishPopup(popup.id); }}
                          >
                            <Play className="mr-2 h-4 w-4" /> Publish
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/popups/${popup.id}/analytics`);
                          }}
                        >
                          <Eye className="mr-2 h-4 w-4" /> Analytics
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => { e.stopPropagation(); duplicatePopup(popup.id); }}
                        >
                          <Copy className="mr-2 h-4 w-4" /> Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={(e) => { e.stopPropagation(); setToDelete(popup.id); }}
                        >
                          <Trash2 className="mr-2 h-4 w-4" /> Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-[13px] text-muted-foreground">
          <span>
            Showing {(page - 1) * perPage + 1} to {Math.min(page * perPage, total)} of {total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline" size="sm" disabled={page <= 1}
              onClick={() => setCurrentPage(page - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline" size="sm" disabled={page >= totalPages}
              onClick={() => setCurrentPage(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      <PopupTemplateDialog
        open={templateOpen}
        onOpenChange={setTemplateOpen}
        onCreated={(id) => navigate(`/popups/${id}/edit`)}
      />

      <Dialog open={!!toDelete} onOpenChange={(open) => !open && setToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this pop-up?</DialogTitle>
            <DialogDescription>
              It stops showing on your site straight away. Its results stay on
              the analytics page.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setToDelete(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => { if (toDelete) deletePopup(toDelete); setToDelete(null); }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
