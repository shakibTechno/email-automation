import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { notificationsApi } from '@/api/notifications';

const QUERY_KEY = ['notifications'] as const;
const COUNT_KEY = ['notifications', 'unread-count'] as const;
const POLL_INTERVAL = 30_000; // 30 seconds

export const useNotifications = () => {
  const queryClient = useQueryClient();

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: notificationsApi.getNotifications,
    staleTime: 15_000,
    refetchInterval: POLL_INTERVAL,
  });

  const { data: unreadCount = 0 } = useQuery({
    queryKey: COUNT_KEY,
    queryFn: notificationsApi.getUnreadCount,
    staleTime: 15_000,
    refetchInterval: POLL_INTERVAL,
  });

  const markReadMutation = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: COUNT_KEY });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: COUNT_KEY });
    },
  });

  return {
    notifications,
    unreadCount,
    isLoading,
    markRead: (id: string) => markReadMutation.mutate(id),
    markAllRead: () => markAllReadMutation.mutate(),
  };
};
