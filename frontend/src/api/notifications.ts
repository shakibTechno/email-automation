import apiClient from './client';
import { Notification, UnreadCountResponse } from '@/types/notification';

export const notificationsApi = {
  getNotifications: async (): Promise<Notification[]> => {
    const response = await apiClient.get<{ results: Notification[] } | Notification[]>(
      '/notifications'
    );
    const raw = response.data as any;
    return raw.results ?? raw;
  },

  getUnreadCount: async (): Promise<number> => {
    const response = await apiClient.get<UnreadCountResponse>(
      '/notifications/unread-count'
    );
    return response.data.unread_count;
  },

  markRead: async (id: string): Promise<void> => {
    await apiClient.post(`/notifications/${id}/mark-read`);
  },

  markAllRead: async (): Promise<void> => {
    await apiClient.post('/notifications/mark-all-read');
  },
};

export default notificationsApi;
