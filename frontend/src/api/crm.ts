import apiClient from './client';
import {
  Pipeline,
  PipelineListItem,
  PipelineAnalytics,
  Stage,
  Deal,
  DealListItem,
  DealListResponse,
  DealContactItem,
  DealStageHistoryItem,
  KanbanStage,
  Activity,
  ActivityListItem,
  ActivityListResponse,
  CreatePipelineData,
  UpdatePipelineData,
  CreateDealData,
  UpdateDealData,
  CreateActivityData,
  UpdateActivityData,
  DealFilters,
  ActivityFilters,
  CRMTask,
  CRMTaskListItem,
  CreateTaskData,
  UpdateTaskData,
  TaskFilters,
  ForecastData,
  Company,
  CompanyListItem,
  CreateCompanyData,
  UpdateCompanyData,
  CompanyFilters,
} from '@/types/crm';
import { PaginationParams } from '@/types/api';

export const crmApi = {
  // ── Pipelines ──

  getPipelines: async (): Promise<PipelineListItem[]> => {
    const response = await apiClient.get('/pipelines');
    return response.data.results ?? response.data;
  },

  getPipeline: async (id: string): Promise<Pipeline> => {
    const response = await apiClient.get<Pipeline>(`/pipelines/${id}`);
    return response.data;
  },

  createPipeline: async (data: CreatePipelineData): Promise<Pipeline> => {
    const response = await apiClient.post<Pipeline>('/pipelines', data);
    return response.data;
  },

  updatePipeline: async (id: string, data: UpdatePipelineData): Promise<Pipeline> => {
    const response = await apiClient.patch<Pipeline>(`/pipelines/${id}`, data);
    return response.data;
  },

  deletePipeline: async (id: string): Promise<void> => {
    await apiClient.delete(`/pipelines/${id}`);
  },

  addStage: async (
    pipelineId: string,
    data: { name: string; color?: string; stage_type?: string; default_probability?: number }
  ): Promise<Stage> => {
    const response = await apiClient.post<Stage>(`/pipelines/${pipelineId}/add_stage`, data);
    return response.data;
  },

  removeStage: async (pipelineId: string, stageId: string): Promise<void> => {
    await apiClient.delete(`/pipelines/${pipelineId}/stages/${stageId}`);
  },

  reorderStages: async (pipelineId: string, stageIds: string[]): Promise<Pipeline> => {
    const response = await apiClient.post<Pipeline>(
      `/pipelines/${pipelineId}/reorder_stages`,
      { stage_ids: stageIds }
    );
    return response.data;
  },

  getKanbanData: async (pipelineId: string): Promise<KanbanStage[]> => {
    const response = await apiClient.get<KanbanStage[]>(`/pipelines/${pipelineId}/kanban`);
    return response.data;
  },

  getPipelineAnalytics: async (pipelineId: string, days?: number): Promise<PipelineAnalytics> => {
    const response = await apiClient.get<PipelineAnalytics>(
      `/pipelines/${pipelineId}/analytics`,
      { params: { days } }
    );
    return response.data;
  },

  // ── Deals ──

  getDeals: async (params?: DealFilters & PaginationParams): Promise<DealListResponse> => {
    const response = await apiClient.get('/deals', { params });
    const raw = response.data;
    const pageSize = params?.page_size ?? 20;
    return {
      data: raw.results ?? raw,
      total: raw.count ?? 0,
      page: params?.page ?? 1,
      per_page: pageSize,
      total_pages: Math.ceil((raw.count ?? 0) / pageSize),
    };
  },

  getDeal: async (id: string): Promise<Deal> => {
    const response = await apiClient.get<Deal>(`/deals/${id}`);
    return response.data;
  },

  createDeal: async (data: CreateDealData): Promise<Deal> => {
    const response = await apiClient.post<Deal>('/deals', data);
    return response.data;
  },

  updateDeal: async (id: string, data: UpdateDealData): Promise<Deal> => {
    const response = await apiClient.patch<Deal>(`/deals/${id}`, data);
    return response.data;
  },

  deleteDeal: async (id: string): Promise<void> => {
    await apiClient.delete(`/deals/${id}`);
  },

  moveDeal: async (id: string, stageId: string, position?: number): Promise<Deal> => {
    const response = await apiClient.post<Deal>(`/deals/${id}/move`, {
      stage_id: stageId,
      ...(position !== undefined ? { position } : {}),
    });
    return response.data;
  },

  winDeal: async (id: string, winReason?: string): Promise<Deal> => {
    const response = await apiClient.post<Deal>(`/deals/${id}/win`, {
      win_reason: winReason || '',
    });
    return response.data;
  },

  loseDeal: async (id: string, lossReason?: string): Promise<Deal> => {
    const response = await apiClient.post<Deal>(`/deals/${id}/lose`, {
      loss_reason: lossReason || '',
    });
    return response.data;
  },

  reopenDeal: async (id: string, stageId?: string): Promise<Deal> => {
    const response = await apiClient.post<Deal>(`/deals/${id}/reopen`, {
      ...(stageId ? { stage_id: stageId } : {}),
    });
    return response.data;
  },

  getDealContacts: async (dealId: string): Promise<DealContactItem[]> => {
    const response = await apiClient.get<DealContactItem[]>(`/deals/${dealId}/contacts`);
    return response.data;
  },

  addDealContact: async (
    dealId: string,
    data: { contact_id: string; role?: string; is_primary?: boolean }
  ): Promise<DealContactItem> => {
    const response = await apiClient.post<DealContactItem>(
      `/deals/${dealId}/contacts`,
      data
    );
    return response.data;
  },

  removeDealContact: async (dealId: string, contactId: string): Promise<void> => {
    await apiClient.delete(`/deals/${dealId}/contacts/${contactId}`);
  },

  getDealActivities: async (dealId: string): Promise<ActivityListItem[]> => {
    const response = await apiClient.get<ActivityListItem[]>(`/deals/${dealId}/activities`);
    return response.data;
  },

  getDealHistory: async (dealId: string): Promise<DealStageHistoryItem[]> => {
    const response = await apiClient.get<DealStageHistoryItem[]>(`/deals/${dealId}/history`);
    return response.data;
  },

  // ── Activities ──

  getActivities: async (params?: ActivityFilters & PaginationParams): Promise<ActivityListResponse> => {
    const response = await apiClient.get('/activities', { params });
    const raw = response.data;
    const pageSize = params?.page_size ?? 20;
    return {
      data: raw.results ?? raw,
      total: raw.count ?? 0,
      page: params?.page ?? 1,
      per_page: pageSize,
      total_pages: Math.ceil((raw.count ?? 0) / pageSize),
    };
  },

  createActivity: async (data: CreateActivityData): Promise<Activity> => {
    const response = await apiClient.post<Activity>('/activities', data);
    return response.data;
  },

  updateActivity: async (id: string, data: UpdateActivityData): Promise<Activity> => {
    const response = await apiClient.patch<Activity>(`/activities/${id}`, data);
    return response.data;
  },

  deleteActivity: async (id: string): Promise<void> => {
    await apiClient.delete(`/activities/${id}`);
  },

  completeActivity: async (id: string): Promise<Activity> => {
    const response = await apiClient.post<Activity>(`/activities/${id}/complete`);
    return response.data;
  },

  // ── Contact integration ──

  getContactDeals: async (contactId: string): Promise<DealListItem[]> => {
    const response = await apiClient.get('/deals', {
      params: { primary_contact: contactId },
    });
    const raw = response.data;
    return raw.results ?? raw;
  },

  // ── CRM Tasks ──

  getTasks: async (params?: TaskFilters & PaginationParams): Promise<CRMTaskListItem[]> => {
    const response = await apiClient.get('/tasks', { params });
    const raw = response.data;
    return raw.results ?? raw;
  },

  getTask: async (id: string): Promise<CRMTask> => {
    const response = await apiClient.get<CRMTask>(`/tasks/${id}`);
    return response.data;
  },

  createTask: async (data: CreateTaskData): Promise<CRMTask> => {
    const response = await apiClient.post<CRMTask>('/tasks', data);
    return response.data;
  },

  updateTask: async (id: string, data: UpdateTaskData): Promise<CRMTask> => {
    const response = await apiClient.patch<CRMTask>(`/tasks/${id}`, data);
    return response.data;
  },

  deleteTask: async (id: string): Promise<void> => {
    await apiClient.delete(`/tasks/${id}`);
  },

  completeTask: async (id: string): Promise<CRMTask> => {
    const response = await apiClient.post<CRMTask>(`/tasks/${id}/complete`);
    return response.data;
  },

  // ── Forecasting ──

  getForecast: async (): Promise<ForecastData> => {
    const response = await apiClient.get<ForecastData>('/pipelines/forecast');
    return response.data;
  },

  // ── Companies ──

  getCompanies: async (params?: CompanyFilters): Promise<CompanyListItem[]> => {
    const response = await apiClient.get('/companies', { params });
    const raw = response.data;
    return raw.results ?? raw;
  },

  getCompany: async (id: string): Promise<Company> => {
    const response = await apiClient.get<Company>(`/companies/${id}`);
    return response.data;
  },

  createCompany: async (data: CreateCompanyData): Promise<Company> => {
    const response = await apiClient.post<Company>('/companies', data);
    return response.data;
  },

  updateCompany: async (id: string, data: UpdateCompanyData): Promise<Company> => {
    const response = await apiClient.patch<Company>(`/companies/${id}`, data);
    return response.data;
  },

  deleteCompany: async (id: string): Promise<void> => {
    await apiClient.delete(`/companies/${id}`);
  },

  getCompanyContacts: async (id: string): Promise<any[]> => {
    const response = await apiClient.get(`/companies/${id}/contacts`);
    return response.data.results ?? response.data;
  },

  getCompanyDeals: async (id: string): Promise<DealListItem[]> => {
    const response = await apiClient.get<DealListItem[]>(`/companies/${id}/deals`);
    return response.data;
  },

  getCompanyActivities: async (id: string): Promise<ActivityListItem[]> => {
    const response = await apiClient.get<ActivityListItem[]>(`/companies/${id}/activities`);
    return response.data;
  },
};

export default crmApi;
