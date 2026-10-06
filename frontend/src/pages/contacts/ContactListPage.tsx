import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Download, Upload, Trash2, GitMerge, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { ContactTable } from '@/components/contacts/ContactTable';
import { ImportContactsDialog } from '@/components/contacts/ImportContactsDialog';
import { DuplicateContactsDialog } from '@/components/contacts/DuplicateContactsDialog';
import { useContacts } from '@/hooks/useContacts';
import { useTeamMembers } from '@/hooks/useTeam';
import { ContactFilters } from '@/types/contact';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { cn, debounce } from '@/lib/utils';

const countFmt = (n: number) => new Intl.NumberFormat('en').format(n ?? 0);

/**
 * The old `subscription_status` filter never worked: the backend FilterSet has
 * no such field, so every value returned the full list. Contact only stores
 * `is_subscribed`, and there is no bounced/complained state on the model — so
 * these are the views the data can actually support.
 */
type ViewKey = 'all' | 'subscribed' | 'unsubscribed' | 'engaged';

const VIEW_PARAMS: Record<ViewKey, Record<string, unknown>> = {
  all: {},
  subscribed: { is_subscribed: true },
  unsubscribed: { is_subscribed: false },
  engaged: { engagement_level: 'high' },
};

const VIEW_LABELS: Array<{ key: ViewKey; label: string }> = [
  { key: 'all', label: 'All contacts' },
  { key: 'subscribed', label: 'Subscribed' },
  { key: 'unsubscribed', label: 'Unsubscribed' },
  { key: 'engaged', label: 'Highly engaged' },
];

export const ContactListPage = () => {
  const navigate = useNavigate();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [view, setView] = useState<ViewKey>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [contactToDelete, setContactToDelete] = useState<string | null>(null);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [assignedToFilter, setAssignedToFilter] = useState<string>('all');

  const { data: members = [] } = useTeamMembers();

  const filters = {
    search: searchQuery || undefined,
    ...VIEW_PARAMS[view],
    assigned_to: assignedToFilter !== 'all' ? assignedToFilter : undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
    page: currentPage,
    per_page: 10,
  } as ContactFilters & { page: number; per_page: number; assigned_to?: string };

  const {
    contacts,
    total,
    page,
    perPage,
    totalPages,
    isLoading,
    deleteContact,
    bulkAction,
    exportContacts,
    isExporting,
  } = useContacts(filters);

  // Real counts per status, so the tiles are filters with true figures rather
  // than decoration. per_page: 1 keeps each one a cheap count query.
  // PaginationParams declares `page_size`, but the API reads `per_page` — the
  // filters above rely on the same widening, so keep the two consistent.
  const countArgs = (key: ViewKey) =>
    ({ ...VIEW_PARAMS[key], page: 1, per_page: 1 }) as ContactFilters & {
      page: number;
      per_page: number;
    };

  const counts: Record<ViewKey, number> = {
    all: useContacts(countArgs('all')).total,
    subscribed: useContacts(countArgs('subscribed')).total,
    unsubscribed: useContacts(countArgs('unsubscribed')).total,
    engaged: useContacts(countArgs('engaged')).total,
  };

  const handleSearch = debounce((value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  }, 300);

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  const handleDelete = (id: string) => {
    setContactToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (contactToDelete) {
      deleteContact(contactToDelete);
      setDeleteDialogOpen(false);
      setContactToDelete(null);
    }
  };

  const handleBulkDelete = () => {
    if (selectedIds.length > 0) {
      bulkAction({ contact_ids: selectedIds, action: 'delete' });
      setSelectedIds([]);
    }
  };

  const handleExport = () => {
    exportContacts(filters);
  };

  return (
    <div className="w-full space-y-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Contacts</h1>
          <p className="text-[13px] text-muted-foreground">
            Everyone in your organization, with status and engagement.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => setDuplicateDialogOpen(true)}>
            <GitMerge className="h-3.5 w-3.5" /> Find duplicates
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport} disabled={isExporting}>
            <Download className="h-3.5 w-3.5" /> {isExporting ? 'Exporting…' : 'Export'}
          </Button>
          <Button variant="outline" size="sm" onClick={() => setImportDialogOpen(true)}>
            <Upload className="h-3.5 w-3.5" /> Import
          </Button>
          <Button size="sm" onClick={() => navigate('/contacts/new')}>
            <Plus className="h-3.5 w-3.5" /> New contact
          </Button>
        </div>
      </div>

      {/* Counts double as the status filter — the figure and the control are the
          same object, so there is nothing to keep in sync. */}
      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
        {VIEW_LABELS.map((tile) => {
          const active = view === tile.key;
          return (
            <button
              key={tile.key}
              type="button"
              aria-pressed={active}
              onClick={() => {
                setView(tile.key);
                setCurrentPage(1);
              }}
              className={cn(
                'rounded-lg border bg-card p-4 text-left shadow-card transition-colors hover:border-brand/40',
                active && 'border-brand bg-brand/[.06]'
              )}
            >
              <span className="stat-label">{tile.label}</span>
              <p className="stat-value text-[22px]">{countFmt(counts[tile.key])}</p>
              <p className="delta">
                {active ? <b className="text-brand">Filtering</b> : <span>Click to filter</span>}
              </p>
            </button>
          );
        })}
      </div>

      <div className="rounded-lg border bg-card shadow-card">
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <Input
            placeholder="Search by email, name, or company…"
            onChange={(e) => handleSearch(e.target.value)}
            className="h-8 max-w-xs flex-1"
          />
          <Select
            value={assignedToFilter}
            onValueChange={(v) => {
              setAssignedToFilter(v);
              setCurrentPage(1);
            }}
          >
            <SelectTrigger className="h-8 w-[180px]">
              <SelectValue placeholder="All assignees" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All assignees</SelectItem>
              {(members as any[]).map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.full_name || m.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {view !== 'all' && (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => {
                setView('all');
                setCurrentPage(1);
              }}
            >
              Clear filter
            </Button>
          )}

          <span className="ml-auto font-mono text-[11px] text-subtle-foreground">
            {countFmt(total)} shown
          </span>
        </div>

        {selectedIds.length > 0 && (
          <div className="flex flex-wrap items-center gap-3 border-b bg-brand/[.08] px-3 py-2.5">
            <span className="text-[12.5px] font-semibold">{selectedIds.length} selected</span>
            <Button variant="destructive" size="sm" onClick={handleBulkDelete}>
              <Trash2 className="h-3.5 w-3.5" /> Delete selected
            </Button>
            <Button variant="outline" size="sm" onClick={() => setSelectedIds([])}>
              Clear selection
            </Button>
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-11 w-full rounded-md" />
            ))}
          </div>
        ) : contacts.length === 0 ? (
          <div className="px-4 py-14 text-center">
            <Users className="mx-auto mb-3 h-6 w-6 text-subtle-foreground" />
            <h3 className="mb-1 text-[14px] font-semibold">No contacts match this view</h3>
            <p className="mb-4 text-[12.5px] text-muted-foreground">
              Try clearing the filters, or import a list to get started.
            </p>
            <div className="flex justify-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setImportDialogOpen(true)}>
                <Upload className="h-3.5 w-3.5" /> Import contacts
              </Button>
              <Button size="sm" onClick={() => navigate('/contacts/new')}>
                <Plus className="h-3.5 w-3.5" /> New contact
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div className="p-1">
              <ContactTable
                contacts={contacts}
                selectedIds={selectedIds}
                onSelectionChange={setSelectedIds}
                onDelete={handleDelete}
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
            </div>

            {totalPages > 1 && (
              <div className="flex flex-wrap items-center justify-between gap-2 border-t px-3 py-2.5">
                <span className="font-mono text-[11px] text-subtle-foreground">
                  {(page - 1) * perPage + 1}–{Math.min(page * perPage, total)} of {countFmt(total)}
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
            <DialogTitle>Delete contact</DialogTitle>
            <DialogDescription>
              This removes the contact and its history. It cannot be undone.
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

      <ImportContactsDialog open={importDialogOpen} onClose={() => setImportDialogOpen(false)} />

      <DuplicateContactsDialog
        open={duplicateDialogOpen}
        onClose={() => setDuplicateDialogOpen(false)}
      />
    </div>
  );
};
