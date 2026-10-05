import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  Plus,
  Search,
  Globe,
  Users,
  Briefcase,
  TrendingUp,
  MoreHorizontal,
  Pencil,
  Trash2,
} from 'lucide-react';
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
import { Badge } from '@/components/ui/badge';
import { CompanyFormDialog } from '@/components/crm/CompanyFormDialog';
import { useCompanies, useCompanyMutations } from '@/hooks/useCRM';
import { CompanyListItem, CreateCompanyData } from '@/types/crm';

const INDUSTRY_LABELS: Record<string, string> = {
  technology: 'Technology',
  financial_services: 'Financial Services',
  healthcare: 'Healthcare',
  retail: 'Retail',
  manufacturing: 'Manufacturing',
  real_estate: 'Real Estate',
  education: 'Education',
  media: 'Media',
  consulting: 'Consulting',
  other: 'Other',
};

export const CompanyListPage = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<CompanyListItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CompanyListItem | null>(null);

  const { data: companies = [], isLoading } = useCompanies(
    search ? { search } : undefined
  );
  const { createCompany, updateCompany, deleteCompany, isCreating, isUpdating, isDeleting } =
    useCompanyMutations();

  const handleCreate = async (data: CreateCompanyData) => {
    await createCompany(data);
    setShowCreate(false);
  };

  const handleUpdate = async (data: CreateCompanyData) => {
    if (!editTarget) return;
    await updateCompany(editTarget.id, data);
    setEditTarget(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteCompany(deleteTarget.id);
    setDeleteTarget(null);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Companies</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your accounts and company relationships
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Company
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-subtle-foreground" />
        <Input
          className="pl-9"
          placeholder="Search companies…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Company</TableHead>
              <TableHead>Industry</TableHead>
              <TableHead>Size</TableHead>
              <TableHead className="text-right">Contacts</TableHead>
              <TableHead className="text-right">Deals</TableHead>
              <TableHead className="text-right">Open Value</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-10 text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            ) : companies.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7}>
                  <div className="flex flex-col items-center justify-center py-12 gap-3">
                    <Building2 className="h-10 w-10 text-subtle-foreground" />
                    <p className="text-muted-foreground text-sm">
                      {search ? 'No companies match your search.' : 'No companies yet. Create your first one!'}
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              companies.map((company) => (
                <TableRow
                  key={company.id}
                  className="cursor-pointer hover:bg-secondary/50"
                  onClick={() => navigate(`/crm/companies/${company.id}`)}
                >
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-full bg-info/[.14] flex items-center justify-center flex-shrink-0">
                        <Building2 className="h-4 w-4 text-brand" />
                      </div>
                      <div>
                        <p className="font-medium text-foreground">{company.name}</p>
                        {company.domain && (
                          <p className="text-xs text-muted-foreground flex items-center gap-1">
                            <Globe className="h-3 w-3" />
                            {company.domain}
                          </p>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {company.industry ? (
                      <Badge variant="secondary" className="text-xs">
                        {INDUSTRY_LABELS[company.industry] ?? company.industry}
                      </Badge>
                    ) : (
                      <span className="text-subtle-foreground text-sm">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {company.size || <span className="text-subtle-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="flex items-center justify-end gap-1 text-sm">
                      <Users className="h-3.5 w-3.5 text-subtle-foreground" />
                      {company.contact_count}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="flex items-center justify-end gap-1 text-sm">
                      <Briefcase className="h-3.5 w-3.5 text-subtle-foreground" />
                      {company.deal_count}
                    </span>
                  </TableCell>
                  <TableCell className="text-right text-sm font-medium">
                    {company.open_deal_value > 0 ? (
                      <span className="flex items-center justify-end gap-1 text-success">
                        <TrendingUp className="h-3.5 w-3.5" />
                        ${company.open_deal_value.toLocaleString()}
                      </span>
                    ) : (
                      <span className="text-subtle-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => setEditTarget(company)}>
                          <Pencil className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => setDeleteTarget(company)}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create Dialog */}
      <CompanyFormDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onSubmit={handleCreate}
        isSubmitting={isCreating}
      />

      {/* Edit Dialog */}
      <CompanyFormDialog
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        onSubmit={handleUpdate}
        initialValues={editTarget ?? undefined}
        isSubmitting={isUpdating}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(v) => !v && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Company</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{deleteTarget?.name}</strong>? This cannot be
              undone. Contacts and deals linked to this company will remain but lose the association.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive hover:bg-destructive/90"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting…' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
