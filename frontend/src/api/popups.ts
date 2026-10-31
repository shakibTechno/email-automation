import apiClient from './client';
import {
  CreatePopupData, Popup, PopupAnalytics, PopupListResponse, PopupTemplate,
  UpdatePopupData,
} from '@/types/popup';

export interface PopupFilters {
  search?: string;
  status?: string;
  popup_type?: string;
  page?: number;
  page_size?: number;
}

export const popupsApi = {
  getPopups: async (filters?: PopupFilters): Promise<PopupListResponse> => {
    const response = await apiClient.get('/popups', { params: filters });
    // DRF paginates; the rest of the app expects this shape.
    const raw = response.data;
    const pageSize = filters?.page_size ?? 20;
    return {
      data: raw.results ?? raw,
      total: raw.count ?? 0,
      page: filters?.page ?? 1,
      per_page: pageSize,
      total_pages: Math.ceil((raw.count ?? 0) / pageSize),
    };
  },

  getPopup: async (id: string): Promise<Popup> => {
    const response = await apiClient.get<Popup>(`/popups/${id}`);
    return response.data;
  },

  createPopup: async (data: CreatePopupData): Promise<Popup> => {
    const response = await apiClient.post<Popup>('/popups', data);
    return response.data;
  },

  updatePopup: async (id: string, data: UpdatePopupData): Promise<Popup> => {
    const response = await apiClient.patch<Popup>(`/popups/${id}`, data);
    return response.data;
  },

  deletePopup: async (id: string): Promise<void> => {
    await apiClient.delete(`/popups/${id}`);
  },

  publishPopup: async (id: string): Promise<Popup> => {
    const response = await apiClient.post<Popup>(`/popups/${id}/publish`);
    return response.data;
  },

  pausePopup: async (id: string): Promise<Popup> => {
    const response = await apiClient.post<Popup>(`/popups/${id}/pause`);
    return response.data;
  },

  duplicatePopup: async (id: string): Promise<Popup> => {
    const response = await apiClient.post<Popup>(`/popups/${id}/duplicate`);
    return response.data;
  },

  getAnalytics: async (id: string, days = 30): Promise<PopupAnalytics> => {
    const response = await apiClient.get<PopupAnalytics>(
      `/popups/${id}/analytics`, { params: { days } },
    );
    return response.data;
  },

  getTemplates: async (): Promise<PopupTemplate[]> => {
    const response = await apiClient.get('/popup-templates');
    return response.data.results ?? response.data;
  },
};

export default popupsApi;
