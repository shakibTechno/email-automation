import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Edit,
  Trophy,
  XCircle,
  RotateCcw,
  Trash2,
  UserPlus,
  Clock,
  DollarSign,
  Percent,
  Calendar,
  User,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DealStatusBadge } from '@/components/crm/DealStatusBadge';
import { PriorityBadge } from '@/components/crm/PriorityBadge';
import { StageProgressBar } from '@/components/crm/StageProgressBar';
import { ActivityTimeline } from '@/components/crm/ActivityTimeline';
import { ActivityFormDialog } from '@/components/crm/ActivityFormDialog';
import { WinLoseDialog } from '@/components/crm/WinLoseDialog';
import { DealFormDialog } from '@/components/crm/DealFormDialog';
import { ContactSearchSelect } from '@/components/crm/ContactSearchSelect';
import { TaskList } from '@/components/crm/TaskList';
import { useDeal, useDealMutations, useActivityMutations } from '@/hooks/useCRM';
import { formatDateTime, formatDate } from '@/lib/utils';

const formatCurrency = (value: number, currency: string) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);
};

export const DealDetailPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const dealId = id || '';
  const { data: deal, isLoading } = useDeal(dealId);
  const {
    updateDeal, deleteDeal, winDeal, loseDeal, reopenDeal,
    addContact, removeContact,
    isUpdating, isWinning, isLosing,
  } = useDealMutations();
  const { createActivity, completeActivity, isCreating: isCreatingActivity } = useActivityMutations();

  const [showEditForm, setShowEditForm] = useState(false);
  const [showActivityForm, setShowActivityForm] = useState(false);
  const [winLoseDialog, setWinLoseDialog] = useState<'win' | 'lose' | null>(null);
  const [showAddContact, setShowAddContact] = useState(false);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!deal) {
    return (
      <div className="p-6 text-center">
        <h2 className="text-2xl font-bold">Deal not found</h2>
        <Button onClick={() => navigate('/crm')} className="mt-4">
          Back to CRM
        </Button>
      </div>
    );
  }

  const handleWin = async (reason: string) => {
    await winDeal(dealId, reason);
    setWinLoseDialog(null);
  };

  const handleLose = async (reason: string) => {
    await loseDeal(dealId, reason);
    setWinLoseDialog(null);
  };

  const handleReopen = async () => {
    await reopenDeal(dealId);
  };

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this deal?')) {
      await deleteDeal(dealId);
      navigate('/crm');
    }
  };

  const handleCreateActivity = async (data: any) => {
    await createActivity(data);
    setShowActivityForm(false);
  };

  const handleAddContact = async (contactId: string | null) => {
    if (contactId) {
      await addContact(dealId, { contact_id: contactId });
      setShowAddContact(false);
    }
  };

  const handleEditDeal = async (data: any) => {
    const { pipeline, stage, contact_ids, ...updateData } = data;
    try {
      await updateDeal(dealId, updateData);
      setShowEditForm(false);
    } catch {
      // error toast handled by mutation
    }
  };

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/crm')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{deal.title}</h1>
              <DealStatusBadge status={deal.status} />
              <PriorityBadge priority={deal.priority} />
              {deal.is_rotting && (
                <span className="flex items-center gap-1 text-xs font-medium text-warning bg-warning/[.10] px-2 py-1 rounded-full border border-warning/[.30]">
                  <AlertTriangle className="h-3 w-3" />
                  Rotting
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              {deal.pipeline_name} &middot; {deal.stage_name}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {deal.status === 'open' && (
            <>
              <Button variant="outline" size="sm" onClick={() => setWinLoseDialog('win')}>
                <Trophy className="h-4 w-4 mr-1" />
                Won
              </Button>
              <Button variant="outline" size="sm" onClick={() => setWinLoseDialog('lose')}>
                <XCircle className="h-4 w-4 mr-1" />
                Lost
              </Button>
            </>
          )}
          {deal.status !== 'open' && (
            <Button variant="outline" size="sm" onClick={handleReopen}>
              <RotateCcw className="h-4 w-4 mr-1" />
              Reopen
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => setShowEditForm(true)}>
            <Edit className="h-4 w-4 mr-1" />
            Edit
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDelete}>
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column (2/3) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          {deal.description && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {deal.description}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Contacts */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-sm">Contacts</CardTitle>
              <Button size="sm" variant="outline" onClick={() => setShowAddContact(!showAddContact)}>
                <UserPlus className="h-4 w-4 mr-1" />
                Add
              </Button>
            </CardHeader>
            <CardContent>
              {showAddContact && (
                <div className="mb-4">
                  <ContactSearchSelect
                    value={null}
                    onChange={handleAddContact}
                    placeholder="Search and add a contact..."
                  />
                </div>
              )}

              {deal.contacts.length === 0 ? (
                <p className="text-sm text-muted-foreground">No contacts linked to this deal.</p>
              ) : (
                <div className="space-y-2">
                  {deal.contacts.map(dc => (
                    <div
                      key={dc.id}
                      className="flex items-center justify-between p-2 rounded-md hover:bg-secondary/50"
                    >
                      <div>
                        <div className="text-sm font-medium">{dc.contact_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {dc.contact_email} &middot; {dc.role.replace('_', ' ')}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeContact(dealId, dc.contact)}
                        className="text-destructive hover:text-destructive"
                      >
                        &times;
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tabs: Activities, Tasks, History */}
          <Tabs defaultValue="activities">
            <TabsList>
              <TabsTrigger value="activities">
                Activities ({deal.activity_count})
              </TabsTrigger>
              <TabsTrigger value="tasks">Tasks</TabsTrigger>
              <TabsTrigger value="history">
                Stage History ({deal.stage_history.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="activities" className="mt-4">
              <Card>
                <CardContent className="p-4">
                  <ActivityTimeline
                    activities={deal.recent_activities}
                    onComplete={(id) => completeActivity(id)}
                    onLogActivity={() => setShowActivityForm(true)}
                  />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="tasks" className="mt-4">
              <Card>
                <CardContent className="p-0">
                  <TaskList dealId={dealId} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="history" className="mt-4">
              <Card>
                <CardContent className="p-4">
                  {deal.stage_history.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No stage changes yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {deal.stage_history.map(h => (
                        <div key={h.id} className="flex items-center gap-3 text-sm">
                          <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
                          <div className="flex-1">
                            <span className="text-muted-foreground">
                              {h.from_stage_name || 'New'} &rarr;{' '}
                            </span>
                            <span className="font-medium">{h.to_stage_name}</span>
                            {h.moved_by_name && (
                              <span className="text-muted-foreground"> by {h.moved_by_name}</span>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground shrink-0">
                            {formatDateTime(h.created_at)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Right column (1/3) */}
        <div className="space-y-6">
          {/* Value card */}
          <Card>
            <CardContent className="p-4 space-y-4">
              <div className="flex items-center gap-3">
                <DollarSign className="h-5 w-5 text-muted-foreground" />
                <div>
                  <div className="text-xl font-bold">
                    {formatCurrency(deal.value, deal.currency)}
                  </div>
                  <div className="text-xs text-muted-foreground">Deal Value</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Percent className="h-5 w-5 text-muted-foreground" />
                <div>
                  <div className="text-lg font-semibold">{deal.probability}%</div>
                  <div className="text-xs text-muted-foreground">
                    Weighted: {formatCurrency(deal.weighted_value, deal.currency)}
                  </div>
                </div>
              </div>

              {deal.close_date && (
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <div className="text-sm font-medium">{formatDate(deal.close_date)}</div>
                    <div className="text-xs text-muted-foreground">Expected Close</div>
                  </div>
                </div>
              )}

              {deal.assigned_to_name && (
                <div className="flex items-center gap-3">
                  <User className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <div className="text-sm font-medium">{deal.assigned_to_name}</div>
                    <div className="text-xs text-muted-foreground">Assigned to</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Stage progress */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Pipeline Progress</CardTitle>
            </CardHeader>
            <CardContent>
              {deal.stages.length > 0 && (
                <StageProgressBar
                  stages={deal.stages}
                  currentStageId={deal.stage}
                />
              )}
            </CardContent>
          </Card>

          {/* Win/loss info */}
          {deal.status === 'won' && deal.win_reason && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm text-success">Win Reason</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{deal.win_reason}</p>
              </CardContent>
            </Card>
          )}

          {deal.status === 'lost' && deal.loss_reason && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm text-destructive">Loss Reason</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{deal.loss_reason}</p>
              </CardContent>
            </Card>
          )}

          {/* Meta info */}
          <Card>
            <CardContent className="p-4 text-xs text-muted-foreground space-y-1">
              {deal.created_by_name && <div>Created by {deal.created_by_name}</div>}
              <div>Created {formatDateTime(deal.created_at)}</div>
              <div>Updated {formatDateTime(deal.updated_at)}</div>
              {deal.closed_at && <div>Closed {formatDateTime(deal.closed_at)}</div>}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dialogs */}
      <WinLoseDialog
        open={winLoseDialog === 'win'}
        onOpenChange={(open) => !open && setWinLoseDialog(null)}
        type="win"
        dealTitle={deal.title}
        onConfirm={handleWin}
        isLoading={isWinning}
      />

      <WinLoseDialog
        open={winLoseDialog === 'lose'}
        onOpenChange={(open) => !open && setWinLoseDialog(null)}
        type="lose"
        dealTitle={deal.title}
        onConfirm={handleLose}
        isLoading={isLosing}
      />

      <ActivityFormDialog
        open={showActivityForm}
        onOpenChange={setShowActivityForm}
        onSubmit={handleCreateActivity}
        isLoading={isCreatingActivity}
        dealId={dealId}
      />

      <DealFormDialog
        open={showEditForm}
        onOpenChange={setShowEditForm}
        pipelineId={deal.pipeline}
        stages={deal.stages}
        onSubmit={handleEditDeal}
        isLoading={isUpdating}
        initialData={deal}
      />
    </div>
  );
};
