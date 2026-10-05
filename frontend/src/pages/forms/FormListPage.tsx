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
  Code,
  ToggleLeft,
  ToggleRight,
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
import { FormStatusBadge } from '@/components/forms/FormStatusBadge';
import { EmbedCodeDialog } from '@/components/forms/EmbedCodeDialog';
import { useForms } from '@/hooks/useForms';
import { FormStatus } from '@/types/form';
import { cn, debounce, formatDate } from '@/lib/utils';

const statusFilters: { value: FormStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];

export const FormListPage = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<FormStatus | 'all'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [formToDelete, setFormToDelete] = useState<string | null>(null);
  const [embedDialogOpen, setEmbedDialogOpen] = useState(false);
  const [embedFormId, setEmbedFormId] = useState<string | null>(null);

  const {
    forms,
    total,
    page,
    perPage,
    totalPages,
    isLoading,
    deleteForm,
    duplicateForm,
    toggleFormStatus,
  } = useForms({
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
    setFormToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (formToDelete) {
      deleteForm(formToDelete);
      setDeleteDialogOpen(false);
      setFormToDelete(null);
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Forms</h1>
          <p className="text-muted-foreground">
            Create and manage lead capture forms
          </p>
        </div>
        <Button onClick={() => navigate('/forms/new')}>
          <Plus className="h-4 w-4 mr-2" />
          Create Form
        </Button>
      </div>

      {/* Filters */}
      <div className="space-y-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search forms..."
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
      ) : forms.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <div className="h-16 w-16 rounded-full bg-secondary flex items-center justify-center mb-4">
            <Plus className="h-8 w-8 text-subtle-foreground" />
          </div>
          <h3 className="text-lg font-medium">No forms yet</h3>
          <p className="text-muted-foreground mt-1 mb-4">
            Create your first lead capture form to get started
          </p>
          <Button onClick={() => navigate('/forms/new')}>
            <Plus className="h-4 w-4 mr-2" />
            Create Form
          </Button>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-secondary/50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    Name
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    Status
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    Type
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    Submissions
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">
                    Created
                  </th>
                  <th className="text-right px-4 py-3 text-sm font-medium text-muted-foreground">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {forms.map((form) => (
                  <tr
                    key={form.id}
                    className="hover:bg-secondary/50 cursor-pointer"
                    onClick={() => navigate(`/forms/${form.id}`)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-sm">{form.name}</div>
                    </td>
                    <td className="px-4 py-3">
                      <FormStatusBadge status={form.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground capitalize">
                      {form.form_type.replace('_', ' ')}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {form.submission_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatDate(form.created_at)}
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
                              navigate(`/forms/${form.id}`);
                            }}
                          >
                            <Eye className="h-4 w-4 mr-2" /> View
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/forms/${form.id}/edit`);
                            }}
                          >
                            <Pencil className="h-4 w-4 mr-2" /> Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleFormStatus(form.id);
                            }}
                          >
                            {form.status === 'active' ? (
                              <>
                                <ToggleLeft className="h-4 w-4 mr-2" /> Deactivate
                              </>
                            ) : (
                              <>
                                <ToggleRight className="h-4 w-4 mr-2" /> Activate
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              setEmbedFormId(form.id);
                              setEmbedDialogOpen(true);
                            }}
                          >
                            <Code className="h-4 w-4 mr-2" /> Embed Code
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              duplicateForm(form.id);
                            }}
                          >
                            <Copy className="h-4 w-4 mr-2" /> Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(form.id);
                            }}
                          >
                            <Trash2 className="h-4 w-4 mr-2" /> Delete
                          </DropdownMenuItem>
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
                {Math.min(page * perPage, total)} of {total} forms
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
            <DialogTitle>Delete Form</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this form? This action cannot be
              undone.
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

      {/* Embed Code Dialog */}
      <EmbedCodeDialog
        formId={embedFormId}
        open={embedDialogOpen}
        onOpenChange={setEmbedDialogOpen}
      />
    </div>
  );
};
