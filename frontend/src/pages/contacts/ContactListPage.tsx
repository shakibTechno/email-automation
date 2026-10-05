import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Download, Upload, Trash2, GitMerge } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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

import { debounce } from '@/lib/utils';

export const ContactListPage = () => {
  const navigate = useNavigate();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [contactToDelete, setContactToDelete] = useState<string | null>(null);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [assignedToFilter, setAssignedToFilter] = useState<string>('all');

  const { data: members = [] } = useTeamMembers();

  const filters: ContactFilters & { page: number; per_page: number; assigned_to?: string } = {
    search: searchQuery || undefined,
    subscription_status: statusFilter !== 'all' ? [statusFilter] : undefined,
    assigned_to: assignedToFilter !== 'all' ? assignedToFilter : undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
    page: currentPage,
    per_page: 10,
  };

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
      bulkAction({
        contact_ids: selectedIds,
        action: 'delete',
      });
      setSelectedIds([]);
    }
  };

  const handleExport = () => {
    exportContacts(filters);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Contacts</h1>
          <p className="text-muted-foreground">
            Manage your email contacts and subscribers
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setDuplicateDialogOpen(true)}>
            <GitMerge className="h-4 w-4 mr-2" />
            Find Duplicates
          </Button>
          <Button variant="outline" onClick={handleExport} disabled={isExporting}>
            <Download className="h-4 w-4 mr-2" />
            {isExporting ? 'Exporting...' : 'Export'}
          </Button>
          <Button variant="outline" onClick={() => setImportDialogOpen(true)}>
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <Button onClick={() => navigate('/contacts/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Contact
          </Button>
        </div>
      </div>

      <div className="flex gap-4 items-center">
        <div className="flex-1">
          <Input
            placeholder="Search by email, name, or company..."
            onChange={(e) => handleSearch(e.target.value)}
            className="max-w-md"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="unsubscribed">Unsubscribed</SelectItem>
            <SelectItem value="bounced">Bounced</SelectItem>
            <SelectItem value="complained">Complained</SelectItem>
          </SelectContent>
        </Select>
        <Select value={assignedToFilter} onValueChange={(v) => { setAssignedToFilter(v); setCurrentPage(1); }}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by assignee" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Assignees</SelectItem>
            {(members as any[]).map((m) => (
              <SelectItem key={m.id} value={m.id}>
                {m.full_name || m.email}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedIds.length > 0 && (
        <div className="flex items-center gap-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <span className="text-sm font-medium">
            {selectedIds.length} contact(s) selected
          </span>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleBulkDelete}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete Selected
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedIds([])}
          >
            Clear Selection
          </Button>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : (
        <>
          <ContactTable
            contacts={contacts}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            onDelete={handleDelete}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
          />

          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Showing {(page - 1) * perPage + 1} to{' '}
                {Math.min(page * perPage, total)} of {total} contacts
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(page - 1)}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(
                      (p) =>
                        p === 1 ||
                        p === totalPages ||
                        (p >= page - 1 && p <= page + 1)
                    )
                    .map((p, i, arr) => (
                      <>
                        {i > 0 && arr[i - 1] !== p - 1 && (
                          <span key={`ellipsis-${p}`} className="px-2">
                            ...
                          </span>
                        )}
                        <Button
                          key={p}
                          variant={p === page ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setCurrentPage(p)}
                        >
                          {p}
                        </Button>
                      </>
                    ))}
                </div>
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

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Contact</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this contact? This action cannot be undone.
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

      <ImportContactsDialog
        open={importDialogOpen}
        onClose={() => setImportDialogOpen(false)}
      />

      <DuplicateContactsDialog
        open={duplicateDialogOpen}
        onClose={() => setDuplicateDialogOpen(false)}
      />
    </div>
  );
};
