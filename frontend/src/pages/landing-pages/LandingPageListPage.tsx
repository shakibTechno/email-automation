import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { Card, CardContent, CardHeader } from '@/components/ui/card';
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
  Search,
  MoreHorizontal,
  Edit,
  Copy,
  Trash2,
  Globe,
  CircleSlash,
  BarChart3,
  ExternalLink,
} from 'lucide-react';
import type { LandingPageStatus } from '@/types/landing-page';

export const LandingPageListPage = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<LandingPageStatus | 'all'>('all');
  const [page, setPage] = useState(1);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);

  const { landingPages, total, isLoading } = useLandingPages({
    search: search || undefined,
    status: statusFilter === 'all' ? undefined : statusFilter,
    page,
  });

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

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this landing page?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Landing Pages</h1>
          <p className="text-muted-foreground">
            Create and manage your landing pages
          </p>
        </div>
        <Button onClick={() => setShowTemplateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Landing Page
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between gap-4">
            {/* Search */}
            <div className="relative w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search landing pages..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              {(['all', 'draft', 'published'] as const).map((status) => (
                <Button
                  key={status}
                  variant={statusFilter === status ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setStatusFilter(status)}
                >
                  {status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : landingPages.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No landing pages found</p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setShowTemplateDialog(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create your first landing page
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>URL</TableHead>
                  <TableHead className="text-right">Views</TableHead>
                  <TableHead className="text-right">Conversions</TableHead>
                  <TableHead>Published</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {landingPages.map((page) => (
                  <TableRow key={page.id}>
                    <TableCell>
                      <button
                        onClick={() => navigate(`/landing-pages/${page.id}`)}
                        className="font-medium hover:text-primary hover:underline text-left"
                      >
                        {page.name}
                      </button>
                    </TableCell>
                    <TableCell>
                      <LandingPageStatusBadge status={page.status} />
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-muted px-2 py-1 rounded">
                        /p/{page.slug}
                      </code>
                    </TableCell>
                    <TableCell className="text-right">
                      {page.view_count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {page.conversion_count.toLocaleString()}
                      {page.view_count > 0 && (
                        <span className="text-muted-foreground ml-1">
                          ({page.conversion_rate}%)
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      {page.published_at ? formatDate(page.published_at) : '-'}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => navigate(`/landing-pages/${page.id}/edit`)}
                          >
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => navigate(`/landing-pages/${page.id}`)}
                          >
                            <BarChart3 className="h-4 w-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          {page.status === 'published' && (
                            <DropdownMenuItem
                              onClick={() => window.open(page.public_url, '_blank')}
                            >
                              <ExternalLink className="h-4 w-4 mr-2" />
                              View Live Page
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          {page.status === 'draft' ? (
                            <DropdownMenuItem
                              onClick={() => publishMutation.mutate(page.id)}
                            >
                              <Globe className="h-4 w-4 mr-2" />
                              Publish
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem
                              onClick={() => unpublishMutation.mutate(page.id)}
                            >
                              <CircleSlash className="h-4 w-4 mr-2" />
                              Unpublish
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem
                            onClick={() => duplicateMutation.mutate(page.id)}
                          >
                            <Copy className="h-4 w-4 mr-2" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => handleDelete(page.id)}
                            className="text-destructive"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {total > 20 && (
            <div className="flex items-center justify-center gap-2 mt-4 pt-4 border-t">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {Math.ceil(total / 20)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= Math.ceil(total / 20)}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Template Selection Dialog */}
      <TemplateSelectionDialog
        open={showTemplateDialog}
        onOpenChange={setShowTemplateDialog}
        onSelect={handleCreate}
        isLoading={createMutation.isPending}
      />
    </div>
  );
};
