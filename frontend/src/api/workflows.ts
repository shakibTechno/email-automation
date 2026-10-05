import apiClient from './client';
import {
  Workflow,
  WorkflowListResponse,
  WorkflowFilters,
  CreateWorkflowData,
  UpdateWorkflowData,
  WorkflowExecution,
  WorkflowExecutionListResponse,
  WorkflowExecutionFilters,
  WorkflowTemplate,
  WorkflowTemplateListResponse,
  WorkflowTemplateFilters,
  WorkflowAnalytics,
  WorkflowValidation,
} from '@/types/workflow';
import { PaginationParams } from '@/types/api';

export const workflowsApi = {
  // Workflows
  getWorkflows: async (
    params?: WorkflowFilters & PaginationParams
  ): Promise<WorkflowListResponse> => {
    const response = await apiClient.get('/workflows', { params });
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

  getWorkflow: async (id: string): Promise<Workflow> => {
    const response = await apiClient.get<Workflow>(`/workflows/${id}`);
    return response.data;
  },

  createWorkflow: async (data: CreateWorkflowData): Promise<Workflow> => {
    const response = await apiClient.post<Workflow>('/workflows', data);
    return response.data;
  },

  updateWorkflow: async (id: string, data: UpdateWorkflowData): Promise<Workflow> => {
    const response = await apiClient.patch<Workflow>(`/workflows/${id}`, data);
    return response.data;
  },

  deleteWorkflow: async (id: string): Promise<void> => {
    await apiClient.delete(`/workflows/${id}`);
  },

  activateWorkflow: async (
    id: string
  ): Promise<{ detail: string; status: string; errors?: string[] }> => {
    const response = await apiClient.post(`/workflows/${id}/activate`);
    return response.data;
  },

  deactivateWorkflow: async (
    id: string
  ): Promise<{ detail: string; status: string }> => {
    const response = await apiClient.post(`/workflows/${id}/deactivate`);
    return response.data;
  },

  duplicateWorkflow: async (id: string): Promise<Workflow> => {
    const response = await apiClient.post<Workflow>(`/workflows/${id}/duplicate`);
    return response.data;
  },

  validateWorkflow: async (id: string): Promise<WorkflowValidation> => {
    const response = await apiClient.get<WorkflowValidation>(
      `/workflows/${id}/validate`
    );
    return response.data;
  },

  getWorkflowAnalytics: async (
    id: string,
    days?: number
  ): Promise<WorkflowAnalytics> => {
    const response = await apiClient.get<WorkflowAnalytics>(
      `/workflows/${id}/analytics`,
      { params: { days } }
    );
    return response.data;
  },

  getWorkflowExecutions: async (
    id: string,
    params?: WorkflowExecutionFilters & PaginationParams
  ): Promise<WorkflowExecutionListResponse> => {
    const response = await apiClient.get(`/workflows/${id}/executions`, { params });
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

  // Workflow Executions (global)
  getExecutions: async (
    params?: WorkflowExecutionFilters & PaginationParams
  ): Promise<WorkflowExecutionListResponse> => {
    const response = await apiClient.get('/workflow-executions', { params });
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

  getExecution: async (id: string): Promise<WorkflowExecution> => {
    const response = await apiClient.get<WorkflowExecution>(
      `/workflow-executions/${id}`
    );
    return response.data;
  },

  cancelExecution: async (id: string): Promise<{ detail: string }> => {
    const response = await apiClient.post(`/workflow-executions/${id}/cancel`);
    return response.data;
  },

  // Workflow Templates
  getTemplates: async (
    params?: WorkflowTemplateFilters & PaginationParams
  ): Promise<WorkflowTemplateListResponse> => {
    const response = await apiClient.get('/workflow-templates', { params });
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

  getTemplate: async (id: string): Promise<WorkflowTemplate> => {
    const response = await apiClient.get<WorkflowTemplate>(
      `/workflow-templates/${id}`
    );
    return response.data;
  },

  useTemplate: async (id: string): Promise<Workflow> => {
    const response = await apiClient.post<Workflow>(
      `/workflow-templates/${id}/use`
    );
    return response.data;
  },
};
