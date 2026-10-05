import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Edit,
  RefreshCw,
  Copy,
  Download,
  Trash2,
  Users,
  Plus,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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
import { Checkbox } from '@/components/ui/checkbox';
import {
  useSegment,
  useSegmentContacts,
  useDeleteSegment,
  useDuplicateSegment,
  useRefreshSegment,
  useExportSegmentContacts,
  useRemoveContactsFromSegment,
  useFieldDefinitions,
} from '@/hooks/useSegments';
import type { SegmentType, SegmentRules, SegmentCondition } from '@/types/segment';

function SegmentTypeBadge({ type }: { type: SegmentType }) {
  const variants: Record<SegmentType, { label: string; className: string }> = {
    dynamic: { label: 'Dynamic', className: 'bg-info/[.14] text-info' },
    static: { label: 'Static', className: 'bg-secondary text-muted-foreground' },
  };

  const { label, className } = variants[type];
  return <Badge className={className}>{label}</Badge>;
}

function formatDate(dateString: string | null) {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function RulesSummary({ rules, fields }: { rules: SegmentRules; fields: any[] }) {
  const getFieldLabel = (field: string) => {
    const f = fields.find((f) => f.field === field);
    return f?.label || field;
  };

  const getOperatorLabel = (field: string, operator: string) => {
    const f = fields.find((f) => f.field === field);
    const op = f?.operators.find((o: any) => o.value === operator);
    return op?.label || operator;
  };

  const renderCondition = (condition: SegmentCondition) => {
    return (
      <div key={condition.id} className="flex items-center gap-2 text-sm py-1">
        <span className="font-medium">{getFieldLabel(condition.field)}</span>
        <span className="text-muted-foreground">
          {getOperatorLabel(condition.field, condition.operator)}
        </span>
        {condition.value !== null && condition.value !== '' && (
          <span className="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">
            {Array.isArray(condition.value)
              ? condition.value.join(', ')
              : String(condition.value)}
          </span>
        )}
      </div>
    );
  };

  if (!rules || !rules.conditions || rules.conditions.length === 0) {
    return <p className="text-muted-foreground">No rules defined</p>;
  }

  return (
    <div className="space-y-1">
      <p className="text-sm text-muted-foreground mb-2">
        Match <strong>{rules.match_type === 'all' ? 'ALL' : 'ANY'}</strong> of the
        following:
      </p>
      {rules.conditions.map(renderCondition)}
    </div>
  );
}

export default function SegmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [page, setPage] = useState(1);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedContacts, setSelectedContacts] = useState<string[]>([]);
  const [showRemoveDialog, setShowRemoveDialog] = useState(false);

  const { data: segment, isLoading: segmentLoading } = useSegment(id!);
  const { data: contactsData, isLoading: contactsLoading } = useSegmentContacts(id!, {
    page,
    page_size: 20,
  });
  const { data: fields = [] } = useFieldDefinitions();

  const deleteSegment = useDeleteSegment();
  const duplicateSegment = useDuplicateSegment();
  const refreshSegment = useRefreshSegment();
  const exportContacts = useExportSegmentContacts();
  const removeContacts = useRemoveContactsFromSegment();

  const handleDelete = () => {
    deleteSegment.mutate(id!, {
      onSuccess: () => navigate('/segments'),
    });
  };

  const handleDuplicate = () => {
    duplicateSegment.mutate(id!, {
      onSuccess: (created) => navigate(`/segments/${created.id}`),
    });
  };

  const handleRefresh = () => {
    refreshSegment.mutate(id!);
  };

  const handleExport = () => {
    if (segment) {
      exportContacts.mutate({ id: id!, name: segment.name });
    }
  };

  const handleRemoveSelected = () => {
    if (selectedContacts.length > 0) {
      removeContacts.mutate(
        { id: id!, data: { contact_ids: selectedContacts } },
        {
          onSuccess: () => {
            setSelectedContacts([]);
            setShowRemoveDialog(false);
          },
        }
      );
    }
  };

  const toggleContactSelection = (contactId: string) => {
    setSelectedContacts((prev) =>
      prev.includes(contactId)
        ? prev.filter((id) => id !== contactId)
        : [...prev, contactId]
    );
  };

  const toggleAllContacts = () => {
    if (!contactsData) return;
    const allIds = contactsData.results.map((c) => c.id);
    if (selectedContacts.length === allIds.length) {
      setSelectedContacts([]);
    } else {
      setSelectedContacts(allIds);
    }
  };

  if (segmentLoading) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center py-12">Loading segment...</div>
      </div>
    );
  }

  if (!segment) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center py-12">Segment not found</div>
      </div>
    );
  }

  const contacts = contactsData?.results || [];
  const totalPages = contactsData?.total_pages || 1;

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/segments')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{segment.name}</h1>
            <SegmentTypeBadge type={segment.segment_type} />
          </div>
          {segment.description && (
            <p className="text-muted-foreground">{segment.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleRefresh}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button variant="outline" onClick={handleDuplicate}>
            <Copy className="mr-2 h-4 w-4" />
            Duplicate
          </Button>
          <Button onClick={() => navigate(`/segments/${id}/edit`)}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button
            variant="destructive"
            size="icon"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content - Contacts */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Contacts</CardTitle>
                <CardDescription>
                  {segment.contact_count.toLocaleString()} contacts in this segment
                </CardDescription>
              </div>
              {segment.segment_type === 'static' && selectedContacts.length > 0 && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setShowRemoveDialog(true)}
                >
                  <X className="mr-2 h-4 w-4" />
                  Remove Selected ({selectedContacts.length})
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {contactsLoading ? (
                <div className="text-center py-8">Loading contacts...</div>
              ) : contacts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No contacts in this segment</p>
                  {segment.segment_type === 'static' && (
                    <Button variant="outline" className="mt-4">
                      <Plus className="mr-2 h-4 w-4" />
                      Add Contacts
                    </Button>
                  )}
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {segment.segment_type === 'static' && (
                          <TableHead className="w-10">
                            <Checkbox
                              checked={selectedContacts.length === contacts.length}
                              onCheckedChange={toggleAllContacts}
                            />
                          </TableHead>
                        )}
                        <TableHead>Email</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Company</TableHead>
                        <TableHead>Engagement</TableHead>
                        <TableHead className="text-right">Lead Score</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {contacts.map((contact) => (
                        <TableRow key={contact.id}>
                          {segment.segment_type === 'static' && (
                            <TableCell>
                              <Checkbox
                                checked={selectedContacts.includes(contact.id)}
                                onCheckedChange={() => toggleContactSelection(contact.id)}
                              />
                            </TableCell>
                          )}
                          <TableCell className="font-medium">{contact.email}</TableCell>
                          <TableCell>
                            {contact.first_name || contact.last_name
                              ? `${contact.first_name || ''} ${contact.last_name || ''}`.trim()
                              : '-'}
                          </TableCell>
                          <TableCell>{contact.company || '-'}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{contact.engagement_level}</Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            {contact.lead_score ?? '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between mt-4">
                      <p className="text-sm text-muted-foreground">
                        Page {page} of {totalPages}
                      </p>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                          disabled={page === 1}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                          disabled={page === totalPages}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Stats Card */}
          <Card>
            <CardHeader>
              <CardTitle>Segment Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Contact Count</p>
                <p className="text-2xl font-bold">
                  {segment.contact_count.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Last Calculated</p>
                <p className="text-sm">{formatDate(segment.last_calculated_at)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Created</p>
                <p className="text-sm">{formatDate(segment.created_at)}</p>
              </div>
              {segment.created_by_name && (
                <div>
                  <p className="text-sm text-muted-foreground">Created By</p>
                  <p className="text-sm">{segment.created_by_name}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Rules Card (Dynamic only) */}
          {segment.segment_type === 'dynamic' && (
            <Card>
              <CardHeader>
                <CardTitle>Rules</CardTitle>
                <CardDescription>Conditions that define this segment</CardDescription>
              </CardHeader>
              <CardContent>
                <RulesSummary rules={segment.rules} fields={fields} />
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Segment</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{segment.name}"? This action cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Remove Contacts Confirmation */}
      <AlertDialog open={showRemoveDialog} onOpenChange={setShowRemoveDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Contacts</AlertDialogTitle>
            <AlertDialogDescription>
              Remove {selectedContacts.length} contact(s) from this segment?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRemoveSelected}>
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
