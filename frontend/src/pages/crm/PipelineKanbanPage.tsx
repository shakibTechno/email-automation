import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Settings, List, LayoutGrid, TrendingUp, DollarSign, Target,
  AlertTriangle, CheckSquare, BarChart2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { KanbanBoard } from '@/components/crm/KanbanBoard';
import { DealFormDialog } from '@/components/crm/DealFormDialog';
import { DealStatusBadge } from '@/components/crm/DealStatusBadge';
import { PriorityBadge } from '@/components/crm/PriorityBadge';
import { TaskList } from '@/components/crm/TaskList';
import {
  usePipelines,
  useKanban,
  usePipelineAnalytics,
  useDealMutations,
  useDeals,
  useForecast,
} from '@/hooks/useCRM';
import { useAuthStore } from '@/stores/authStore';
import { DealFilters, Stage } from '@/types/crm';
import { cn, formatDate } from '@/lib/utils';

const formatCurrency = (value: number) => {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
};

export const PipelineKanbanPage = () => {
  const navigate = useNavigate();
  const { data: pipelines, isLoading: loadingPipelines } = usePipelines();
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>('');
  const [viewMode, setViewMode] = useState<'kanban' | 'list'>('kanban');
  const [showDealForm, setShowDealForm] = useState(false);
  const [defaultStageId, setDefaultStageId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [myDealsOnly, setMyDealsOnly] = useState(false);
  const currentUser = useAuthStore((s) => s.user);

  // Set default pipeline
  useEffect(() => {
    if (pipelines && pipelines.length > 0 && !selectedPipelineId) {
      const defaultPipeline = pipelines.find(p => p.is_default) || pipelines[0];
      setSelectedPipelineId(defaultPipeline.id);
    }
  }, [pipelines, selectedPipelineId]);

  const { kanbanData, isLoading: loadingKanban, moveDeal } = useKanban(selectedPipelineId);
  const { data: analytics } = usePipelineAnalytics(selectedPipelineId, 30);
  const { createDeal, isCreating } = useDealMutations();
  const { data: forecast } = useForecast();

  const listFilters: DealFilters = {
    pipeline: selectedPipelineId,
    search: searchQuery || undefined,
    ...(myDealsOnly && currentUser ? { assigned_to: currentUser.id } : {}),
  };

  // List view data
  const { deals: listDeals } = useDeals(viewMode === 'list' ? listFilters : undefined);

  // Collect stages from kanban data
  const stages: Stage[] = kanbanData.map(col => col.stage);

  const handleDragEnd = (dealId: string, toStageId: string, newIndex: number) => {
    moveDeal(dealId, toStageId, newIndex);
  };

  const handleAddDeal = (stageId: string) => {
    setDefaultStageId(stageId);
    setShowDealForm(true);
  };

  const handleCreateDeal = async (data: any) => {
    try {
      await createDeal(data);
      setShowDealForm(false);
    } catch {
      // Error handled by mutation
    }
  };

  if (loadingPipelines) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">CRM Pipeline</h1>
          {pipelines && pipelines.length > 1 && (
            <Select value={selectedPipelineId} onValueChange={setSelectedPipelineId}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select pipeline" />
              </SelectTrigger>
              <SelectContent>
                {pipelines.map(p => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => navigate('/crm/settings')}>
            <Settings className="h-4 w-4" />
          </Button>
          <Button onClick={() => { setDefaultStageId(''); setShowDealForm(true); }}>
            <Plus className="h-4 w-4 mr-2" />
            Add Deal
          </Button>
        </div>
      </div>

      {/* Stats bar — same tile object as the Dashboard and Contacts, so the
          three screens read as one system rather than three designs. */}
      {analytics && (
        <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
          {[
            {
              label: 'Open deals',
              value: analytics.summary.open_deals_count,
              note: 'in this pipeline',
              icon: Target,
            },
            {
              label: 'Pipeline value',
              value: formatCurrency(analytics.summary.open_deals_value),
              note: 'open deals, unweighted',
              icon: DollarSign,
            },
            {
              label: 'Win rate (30d)',
              value: `${analytics.win_rate.toFixed(0)}%`,
              note: 'closed won vs lost',
              icon: TrendingUp,
            },
            {
              label: 'Rotting deals',
              value: forecast?.rotting_deals_count ?? 0,
              note: 'no recent activity',
              icon: AlertTriangle,
              warn: (forecast?.rotting_deals_count ?? 0) > 0,
            },
          ].map((tile) => (
            <div key={tile.label} className="rounded-lg border bg-card p-4 shadow-card">
              <div className="flex items-center gap-2">
                <span className="stat-label">{tile.label}</span>
                <tile.icon
                  className={cn(
                    'ml-auto h-3.5 w-3.5',
                    tile.warn ? 'text-warning' : 'text-subtle-foreground'
                  )}
                />
              </div>
              <p className="stat-value text-[22px]">{tile.value}</p>
              <p className={cn('delta', tile.warn && 'delta-down')}>
                <span>{tile.note}</span>
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Main tabs: Pipeline, Tasks, Forecast */}
      <Tabs defaultValue="pipeline">
        <TabsList>
          <TabsTrigger value="pipeline" className="gap-2">
            <LayoutGrid className="h-4 w-4" />
            Pipeline
          </TabsTrigger>
          <TabsTrigger value="tasks" className="gap-2">
            <CheckSquare className="h-4 w-4" />
            My Tasks
          </TabsTrigger>
          <TabsTrigger value="forecast" className="gap-2">
            <BarChart2 className="h-4 w-4" />
            Forecast
          </TabsTrigger>
        </TabsList>

        {/* Pipeline tab */}
        <TabsContent value="pipeline" className="mt-4 space-y-4">
          {/* View mode toggle + search */}
          <div className="flex items-center justify-between">
            <div className="flex border rounded-md overflow-hidden">
              <button
                className={`px-3 py-1.5 text-sm ${viewMode === 'kanban' ? 'bg-primary text-primary-foreground' : 'bg-card'}`}
                onClick={() => setViewMode('kanban')}
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                className={`px-3 py-1.5 text-sm ${viewMode === 'list' ? 'bg-primary text-primary-foreground' : 'bg-card'}`}
                onClick={() => setViewMode('list')}
              >
                <List className="h-4 w-4" />
              </button>
            </div>
            {viewMode === 'list' && (
              <div className="flex items-center gap-2">
                <Button
                  variant={myDealsOnly ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setMyDealsOnly(!myDealsOnly)}
                >
                  My Deals
                </Button>
                <Input
                  placeholder="Search deals..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="max-w-xs"
                />
              </div>
            )}
          </div>

          {viewMode === 'kanban' ? (
            loadingKanban ? (
              <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : (
              <KanbanBoard
                columns={kanbanData}
                onDragEnd={handleDragEnd}
                onAddDeal={handleAddDeal}
              />
            )
          ) : (
            <Card>
              <CardContent className="p-0">
                <table className="w-full">
                  <thead>
                    <tr className="border-b text-left text-xs text-muted-foreground">
                      <th className="p-3 font-medium">Deal</th>
                      <th className="p-3 font-medium">Stage</th>
                      <th className="p-3 font-medium">Value</th>
                      <th className="p-3 font-medium">Priority</th>
                      <th className="p-3 font-medium">Status</th>
                      <th className="p-3 font-medium">Contact</th>
                      <th className="p-3 font-medium">Close Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {listDeals.map(deal => (
                      <tr
                        key={deal.id}
                        className="border-b hover:bg-secondary/50 cursor-pointer transition-colors"
                        onClick={() => navigate(`/crm/deals/${deal.id}`)}
                      >
                        <td className="p-3">
                          <div className="flex items-center gap-1.5">
                            <span className="font-medium text-sm">{deal.title}</span>
                            {deal.is_rotting && (
                              <AlertTriangle className="h-3.5 w-3.5 text-warning shrink-0" />
                            )}
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-1.5 text-sm">
                            <div className="h-2 w-2 rounded-full" style={{ backgroundColor: deal.stage_color }} />
                            {deal.stage_name}
                          </div>
                        </td>
                        <td className="p-3 text-sm font-medium">
                          {deal.value > 0 ? formatCurrency(deal.value) : '-'}
                        </td>
                        <td className="p-3"><PriorityBadge priority={deal.priority} /></td>
                        <td className="p-3"><DealStatusBadge status={deal.status} /></td>
                        <td className="p-3 text-sm text-muted-foreground">{deal.primary_contact_name || '-'}</td>
                        <td className="p-3 text-sm text-muted-foreground">
                          {deal.close_date ? formatDate(deal.close_date) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* My Tasks tab */}
        <TabsContent value="tasks" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">My Tasks</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <TaskList showAddButton />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Forecast tab */}
        <TabsContent value="forecast" className="mt-4 space-y-6">
          {forecast ? (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="text-xs text-muted-foreground mb-1">Weighted Forecast</div>
                    <div className="text-2xl font-bold text-primary">
                      {formatCurrency(forecast.total_weighted)}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Based on probability × value
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="text-xs text-muted-foreground mb-1">Best Case</div>
                    <div className="text-2xl font-bold text-success">
                      {formatCurrency(forecast.total_best_case)}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      If all deals close
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="text-xs text-muted-foreground mb-1">Open Deals</div>
                    <div className="text-2xl font-bold">{forecast.open_deals_count}</div>
                    <div className="text-xs text-warning mt-1 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      {forecast.rotting_deals_count} rotting
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Bar chart */}
              {forecast.buckets.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Revenue by Close Month</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart
                        data={forecast.buckets}
                        margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                        <YAxis
                          tickFormatter={(v) => formatCurrency(v)}
                          tick={{ fontSize: 11 }}
                        />
                        <Tooltip
                          formatter={(value: number | undefined, name: string | undefined) => [
                            formatCurrency(value ?? 0),
                            name === 'weighted' ? 'Weighted' : 'Best Case',
                          ]}
                        />
                        <Legend
                          formatter={(value) => value === 'weighted' ? 'Weighted' : 'Best Case'}
                        />
                        <Bar dataKey="weighted" fill="#6366f1" radius={[3, 3, 0, 0]} />
                        <Bar dataKey="best_case" fill="#22c55e" radius={[3, 3, 0, 0]} opacity={0.6} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}

              {/* Bucket table */}
              <Card>
                <CardContent className="p-0">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs text-muted-foreground">
                        <th className="p-3 font-medium">Month</th>
                        <th className="p-3 font-medium text-right">Deals</th>
                        <th className="p-3 font-medium text-right">Weighted</th>
                        <th className="p-3 font-medium text-right">Best Case</th>
                      </tr>
                    </thead>
                    <tbody>
                      {forecast.buckets.map((b) => (
                        <tr key={b.month ?? 'no-date'} className="border-b last:border-0 hover:bg-secondary/50">
                          <td className="p-3 font-medium">{b.label}</td>
                          <td className="p-3 text-right text-muted-foreground">{b.deal_count}</td>
                          <td className="p-3 text-right font-medium text-primary">
                            {formatCurrency(b.weighted)}
                          </td>
                          <td className="p-3 text-right text-success">
                            {formatCurrency(b.best_case)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </>
          ) : (
            <div className="flex justify-center items-center h-32 text-muted-foreground text-sm">
              Loading forecast...
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Deal creation dialog */}
      <DealFormDialog
        open={showDealForm}
        onOpenChange={setShowDealForm}
        pipelineId={selectedPipelineId}
        stages={stages}
        onSubmit={handleCreateDeal}
        isLoading={isCreating}
        defaultStageId={defaultStageId}
      />
    </div>
  );
};
