import { useMemo, useState } from 'react';
import { MoreVertical, Pencil, Plus, Tags, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { TagChip } from '@/components/contacts/TagChip';
import { TagFormDialog } from '@/components/contacts/TagFormDialog';
import { useTags } from '@/hooks/useTags';
import { cn } from '@/lib/utils';
import type { CreateTagData, Tag } from '@/types/contact';

const countFmt = (n: number) => new Intl.NumberFormat('en').format(n ?? 0);

const usageOf = (tag: Tag) => tag.contact_count ?? 0;

const formatDate = (value?: string) =>
  value
    ? new Date(value).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : '—';

/**
 * The tiles are the filter, as on Contacts: the figure and the control are the
 * same object, so there is nothing to keep in sync. "Unused" is the one most
 * worth surfacing — an unused tag is the only tag that is safe to delete, and
 * it was invisible on the old grid of identical coloured pills.
 */
type ViewKey = 'all' | 'in_use' | 'unused';

const VIEW_LABELS: Array<{ key: ViewKey; label: string; hint: string }> = [
  { key: 'all', label: 'All tags', hint: 'Every tag in the organization' },
  { key: 'in_use', label: 'In use', hint: 'Applied to at least one contact' },
  { key: 'unused', label: 'Unused', hint: 'Applied to nobody' },
];

type SortKey = 'name' | 'usage' | 'newest';

export const TagManagementPage = () => {
  const { tags, isLoading, createTag, updateTag, deleteTag, isCreating, isUpdating, isDeleting } =
    useTags();

  const [search, setSearch] = useState('');
  const [view, setView] = useState<ViewKey>('all');
  const [sort, setSort] = useState<SortKey>('name');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Tag | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Tag | null>(null);

  const counts = useMemo(
    () => ({
      all: tags.length,
      in_use: tags.filter((tag) => usageOf(tag) > 0).length,
      unused: tags.filter((tag) => usageOf(tag) === 0).length,
    }),
    [tags]
  );

  // Every tag is already in memory — the endpoint is unpaginated reference
  // data — so filtering and sorting here keeps the list instant and avoids a
  // request per keystroke.
  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const filtered = tags.filter((tag) => {
      if (view === 'in_use' && usageOf(tag) === 0) return false;
      if (view === 'unused' && usageOf(tag) > 0) return false;
      if (!needle) return true;
      return (
        tag.name.toLowerCase().includes(needle) ||
        (tag.description ?? '').toLowerCase().includes(needle)
      );
    });

    const sorted = [...filtered];
    if (sort === 'name') {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sort === 'usage') {
      sorted.sort((a, b) => usageOf(b) - usageOf(a) || a.name.localeCompare(b.name));
    } else {
      sorted.sort((a, b) => new Date(b.created_at).valueOf() - new Date(a.created_at).valueOf());
    }
    return sorted;
  }, [tags, search, view, sort]);

  const isFiltered = view !== 'all' || search.trim().length > 0;

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  const openEdit = (tag: Tag) => {
    setEditing(tag);
    setFormOpen(true);
  };

  // Closing on success rather than on click: a name that clashes with an
  // existing tag is rejected by the server, and the old page threw that away
  // by closing and clearing the form regardless.
  const handleSubmit = (data: CreateTagData) => {
    if (editing) {
      updateTag(editing.id, data, { onSuccess: () => setFormOpen(false) });
    } else {
      createTag(data, { onSuccess: () => setFormOpen(false) });
    }
  };

  const confirmDelete = () => {
    if (!pendingDelete) return;
    deleteTag(pendingDelete.id, { onSuccess: () => setPendingDelete(null) });
  };

  const deleteUsage = pendingDelete ? usageOf(pendingDelete) : 0;

  return (
    <div className="w-full space-y-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tags</h1>
          <p className="text-[13px] text-muted-foreground">
            Labels you apply to contacts, and how widely each one is used.
          </p>
        </div>
        <Button size="sm" onClick={openCreate}>
          <Plus className="h-3.5 w-3.5" /> New tag
        </Button>
      </div>

      <div className="grid gap-3.5 sm:grid-cols-3">
        {VIEW_LABELS.map((tile) => {
          const active = view === tile.key;
          return (
            <button
              key={tile.key}
              type="button"
              aria-pressed={active}
              onClick={() => setView(tile.key)}
              className={cn(
                'rounded-lg border bg-card p-4 text-left shadow-card transition-colors hover:border-brand/40',
                active && 'border-brand bg-brand/[.06]'
              )}
            >
              <span className="stat-label">{tile.label}</span>
              <p className="stat-value text-[22px]">{countFmt(counts[tile.key])}</p>
              <p className="delta">
                {active ? <b className="text-brand">Filtering</b> : <span>{tile.hint}</span>}
              </p>
            </button>
          );
        })}
      </div>

      <div className="rounded-lg border bg-card shadow-card">
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <Input
            placeholder="Search tags…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 max-w-xs flex-1"
          />
          <Select value={sort} onValueChange={(value) => setSort(value as SortKey)}>
            <SelectTrigger className="h-8 w-[170px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Name A–Z</SelectItem>
              <SelectItem value="usage">Most used</SelectItem>
              <SelectItem value="newest">Newest first</SelectItem>
            </SelectContent>
          </Select>

          {isFiltered && (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => {
                setView('all');
                setSearch('');
              }}
            >
              Clear filter
            </Button>
          )}

          <span className="ml-auto font-mono text-[11px] text-subtle-foreground">
            {countFmt(visible.length)} shown
          </span>
        </div>

        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-11 w-full rounded-md" />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <div className="px-4 py-14 text-center">
            <Tags className="mx-auto mb-3 h-6 w-6 text-subtle-foreground" />
            <h3 className="mb-1 text-[14px] font-semibold">
              {isFiltered ? 'No tags match this view' : 'No tags yet'}
            </h3>
            <p className="mb-4 text-[12.5px] text-muted-foreground">
              {isFiltered
                ? 'Try clearing the search or the filter above.'
                : 'Tags let you group contacts by interest, source or lifecycle stage, then segment on them.'}
            </p>
            <div className="flex justify-center gap-2">
              {isFiltered ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setView('all');
                    setSearch('');
                  }}
                >
                  Clear filter
                </Button>
              ) : (
                <Button size="sm" onClick={openCreate}>
                  <Plus className="h-3.5 w-3.5" /> Create your first tag
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="p-1">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tag</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Contacts</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((tag) => {
                  const usage = usageOf(tag);
                  return (
                    <TableRow key={tag.id}>
                      <TableCell>
                        <TagChip tag={tag} />
                      </TableCell>
                      <TableCell className="max-w-[320px]">
                        {tag.description ? (
                          <span className="line-clamp-2 text-[12.5px] text-muted-foreground">
                            {tag.description}
                          </span>
                        ) : (
                          <span className="text-[12.5px] text-subtle-foreground">—</span>
                        )}
                      </TableCell>
                      {/* An unused tag is the actionable case, so it reads as a
                          word rather than as the figure zero. */}
                      <TableCell className="text-right">
                        {usage > 0 ? (
                          <span className="font-medium">{countFmt(usage)}</span>
                        ) : (
                          <span className="text-subtle-foreground">Unused</span>
                        )}
                      </TableCell>
                      <TableCell className="text-[12.5px] text-muted-foreground">
                        {formatDate(tag.created_at)}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label={`Actions for ${tag.name}`}
                            >
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => openEdit(tag)}>
                              <Pencil className="mr-2 h-4 w-4" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => setPendingDelete(tag)}
                              className="text-destructive"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      <TagFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        tag={editing}
        onSubmit={handleSubmit}
        isSubmitting={editing ? isUpdating : isCreating}
        existingNames={tags.filter((tag) => tag.id !== editing?.id).map((tag) => tag.name)}
      />

      <AlertDialog open={!!pendingDelete} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete “{pendingDelete?.name}”?</AlertDialogTitle>
            {/* The old copy warned about "all contacts" whether or not the tag
                was on any. The real number is what decides it. */}
            <AlertDialogDescription>
              {deleteUsage > 0
                ? `This tag is applied to ${countFmt(deleteUsage)} ${
                    deleteUsage === 1 ? 'contact' : 'contacts'
                  }. Deleting it removes it from all of them, and from any segment or workflow that refers to it. This cannot be undone.`
                : 'This tag is not applied to any contact. Deleting it cannot be undone.'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                // Keep the dialog open until the request lands, so a failure is
                // visible instead of the row quietly staying put.
                e.preventDefault();
                confirmDelete();
              }}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? 'Deleting…' : 'Delete tag'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
