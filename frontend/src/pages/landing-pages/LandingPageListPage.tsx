import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
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
import { LandingPageStatusBadge } from '@/components/landing-pages/LandingPageStatusBadge';
import { TemplateSelectionDialog } from '@/components/landing-pages/TemplateSelectionDialog';
import {
  useLandingPages,
  useCreateLandingPage,
  useDeleteLandingPage,
  usePublishLandingPage,
  useUnpublishLandingPage,
  useDuplicateLandingPage,
} from '@/hooks/useLandingPages';
import {
  Plus,
  MoreHorizontal,
  Edit,
  Copy,
  Trash2,
  Globe,
  CircleSlash,
  BarChart3,
  ExternalLink,
  Check,
  Layout,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import type { LandingPage, LandingPageStatus } from '@/types/landing-page';

const countFmt = (n: number) => new Intl.NumberFormat('en').format(n ?? 0);

const formatDate = (value?: string | null) =>
  value
    ? new Date(value).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : '—';

type ViewKey = 'all' | 'published' | 'draft';

const VIEW_LABELS: Array<{ key: ViewKey; label: string; hint: string }> = [
  { key: 'all', label: 'All pages', hint: 'Every page in the organization' },
  { key: 'published', label: 'Live', hint: 'Reachable at their public URL' },
  { key: 'draft', label: 'Drafts', hint: 'Not published yet' },
];

export const LandingPageListPage = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [view, setView] = useState<ViewKey>('all');
  const [page, setPage] = useState(1);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<LandingPage | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const { landingPages, total, isLoading } = useLandingPages({
    search: search || undefined,
    status: view === 'all' ? undefined : (view as LandingPageStatus),
    page,
  });

  // Counts for the tiles. The list endpoint is filtered server-side, so each
  // view is its own cheap count query rather than something derived from the
  // current page of results.
  const publishedCount = useLandingPages({ status: 'published', page: 1 }).total;
  const draftCount = useLandingPages({ status: 'draft', page: 1 }).total;
  const allCount = useLandingPages({ page: 1 }).total;

  const counts: Record<ViewKey, number> = useMemo(
    () => ({ all: allCount, published: publishedCount, draft: draftCount }),
    [allCount, publishedCount, draftCount]
  );

  const createMutation = useCreateLandingPage();
  const deleteMutation = useDeleteLandingPage();
  const publishMutation = usePublishLandingPage();
  const unpublishMutation = useUnpublishLandingPage();
  const duplicateMutation = useDuplicateLandingPage();

  const handleCreate = async (templateId: string | null, name: string) => {
    const result = await createMutation.mutateAsync({
      name,
      template_id: templateId || undefined,
    });
    setShowTemplateDialog(false);
    navigate(`/landing-pages/${result.id}/edit`);
  };

  // "Give me the link" is the most common thing anyone wants from a published
  // page, and it used to be buried two levels into the row menu.
  const copyUrl = async (item: LandingPage) => {
    if (!item.public_url) return;
    try {
      await navigator.clipboard.writeText(item.public_url);
      setCopiedId(item.id);
      setTimeout(() => setCopiedId((id) => (id === item.id ? null : id)), 2000);
    } catch {
      toast.error('Could not copy the link');
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / 20));
  const isFiltered = view !== 'all' || search.trim().length > 0;

  const clearFilters = () => {
    setView('all');
    setSearch('');
    setPage(1);
  };

  return (
    <div className="w-full space-y-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Landing Pages</h1>
          <p className="text-[13px] text-muted-foreground">
            Standalone pages that capture leads, and how each one is performing.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowTemplateDialog(true)}>
          <Plus className="h-3.5 w-3.5" /> New page
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
              onClick={() => {
                setView(tile.key);
                setPage(1);
              }}
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
            placeholder="Search landing pages…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="h-8 max-w-xs flex-1"
          />
          {isFiltered && (
            <Button variant="outline" size="sm" className="h-8" onClick={clearFilters}>
              Clear filter
            </Button>
          )}
          <span className="ml-auto font-mono text-[11px] text-subtle-foreground">
            {countFmt(total)} shown
          </span>
        </div>

        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-11 w-full rounded-md" />
            ))}
          </div>
        ) : landingPages.length === 0 ? (
          <div className="px-4 py-14 text-center">
            <Layout className="mx-auto mb-3 h-6 w-6 text-subtle-foreground" />
            <h3 className="mb-1 text-[14px] font-semibold">
              {isFiltered ? 'No pages match this view' : 'No landing pages yet'}
            </h3>
            <p className="mb-4 text-[12.5px] text-muted-foreground">
              {isFiltered
                ? 'Try clearing the search or the filter above.'
                : 'A landing page is a standalone page with a form on it — the usual way to turn traffic into contacts.'}
            </p>
            <div className="flex justify-center gap-2">
              {isFiltered ? (
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear filter
                </Button>
              ) : (
                <Button size="sm" onClick={() => setShowTemplateDialog(true)}>
                  <Plus className="h-3.5 w-3.5" /> Create your first page
                </Button>
              )}
            </div>
          </div>
        ) : (
          <>
            <div className="px-4 pb-2 pt-3 [&_tr>*:last-child]:pr-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-full">Name</TableHead>
                    <TableHead className="whitespace-nowrap">Status</TableHead>
                    <TableHead className="whitespace-nowrap">URL</TableHead>
                    <TableHead className="whitespace-nowrap text-right">Views</TableHead>
                    <TableHead className="whitespace-nowrap text-right">Conversions</TableHead>
                    <TableHead className="whitespace-nowrap">Published</TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {landingPages.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <button
                          onClick={() => navigate(`/landing-pages/${item.id}`)}
                          className="text-left font-medium text-foreground hover:underline"
                        >
                          {item.name}
                        </button>
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <LandingPageStatusBadge status={item.status} />
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => copyUrl(item)}
                          title={`Copy ${item.public_url}`}
                          className="inline-flex items-center gap-1.5 rounded-[5px] border bg-secondary px-2 py-0.5 font-mono text-[11px] text-muted-foreground transition-colors hover:text-foreground"
                        >
                          /p/{item.slug}
                          {copiedId === item.id ? (
                            <Check className="h-3 w-3 text-success" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </button>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-right font-medium">
                        {countFmt(item.view_count)}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-right">
                        <span className="font-medium">{countFmt(item.conversion_count)}</span>
                        {item.view_count > 0 && (
                          <span className="ml-1 text-subtle-foreground">
                            ({item.conversion_rate}%)
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-[12.5px] text-muted-foreground">
                        {formatDate(item.published_at)}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label={`Actions for ${item.name}`}
                            >
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => navigate(`/landing-pages/${item.id}/edit`)}
                            >
                              <Edit className="mr-2 h-4 w-4" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => navigate(`/landing-pages/${item.id}`)}
                            >
                              <BarChart3 className="mr-2 h-4 w-4" />
                              View details
                            </DropdownMenuItem>
                            {item.status === 'published' && (
                              <DropdownMenuItem
                                onClick={() => window.open(item.public_url, '_blank')}
                              >
                                <ExternalLink className="mr-2 h-4 w-4" />
                                Open live page
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            {item.status === 'draft' ? (
                              <DropdownMenuItem
                                onClick={() => publishMutation.mutate(item.id)}
                              >
                                <Globe className="mr-2 h-4 w-4" />
                                Publish
                              </DropdownMenuItem>
                            ) : (
                              <DropdownMenuItem
                                onClick={() => unpublishMutation.mutate(item.id)}
                              >
                                <CircleSlash className="mr-2 h-4 w-4" />
                                Unpublish
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem
                              onClick={() => duplicateMutation.mutate(item.id)}
                            >
                              <Copy className="mr-2 h-4 w-4" />
                              Duplicate
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => setPendingDelete(item)}
                              className="text-destructive"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {total > 20 && (
              <div className="flex flex-wrap items-center justify-between gap-2 border-t px-3 py-2.5">
                <span className="font-mono text-[11px] text-subtle-foreground">
                  {(page - 1) * 20 + 1}–{Math.min(page * 20, total)} of {countFmt(total)}
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8"
                    disabled={page === 1}
                    onClick={() => setPage(page - 1)}
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
                    disabled={page >= totalPages}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <TemplateSelectionDialog
        open={showTemplateDialog}
        onOpenChange={setShowTemplateDialog}
        onSelect={handleCreate}
        // A generated page already exists by the time this fires — the job
        // created it — so there is nothing to create, only somewhere to go.
        onGenerated={(id) => navigate(`/landing-pages/${id}/edit`)}
        isLoading={createMutation.isPending}
      />

      {/* Replaces a `window.confirm`, which is the only place in the app that
          still used one and gave no sense of what was being lost. */}
      <AlertDialog
        open={!!pendingDelete}
        onOpenChange={(open) => !open && setPendingDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete “{pendingDelete?.name}”?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete?.status === 'published'
                ? `This page is live at /p/${pendingDelete?.slug}. Deleting it takes it offline immediately, and anyone following that link will get a 404. Its view and conversion history goes too. This cannot be undone.`
                : 'This removes the page and its design. This cannot be undone.'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                if (!pendingDelete) return;
                deleteMutation.mutate(pendingDelete.id, {
                  onSuccess: () => setPendingDelete(null),
                });
              }}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting…' : 'Delete page'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
