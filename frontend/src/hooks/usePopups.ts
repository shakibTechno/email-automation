import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { popupsApi, PopupFilters } from '@/api/popups';
import { CreatePopupData, UpdatePopupData } from '@/types/popup';

export const usePopups = (filters?: PopupFilters) => {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['popups', filters],
    queryFn: () => popupsApi.getPopups(filters),
    staleTime: 30000,
  });

  const invalidate = (id?: string) => {
    queryClient.invalidateQueries({ queryKey: ['popups'] });
    if (id) queryClient.invalidateQueries({ queryKey: ['popup', id] });
  };

  // Every mutation below reports its own failure. A dialog that closes on
  // success and does nothing on error reads as an unwired button.
  const createMutation = useMutation({
    mutationFn: (payload: CreatePopupData) => popupsApi.createPopup(payload),
    onSuccess: () => { invalidate(); toast.success('Pop-up created'); },
    onError: (e: any) => toast.error(e.message || 'Could not create the pop-up'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdatePopupData }) =>
      popupsApi.updatePopup(id, data),
    onSuccess: (_, vars) => { invalidate(vars.id); toast.success('Saved'); },
    onError: (e: any) => toast.error(e.message || 'Could not save the pop-up'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => popupsApi.deletePopup(id),
    onSuccess: () => { invalidate(); toast.success('Pop-up deleted'); },
    onError: (e: any) => toast.error(e.message || 'Could not delete the pop-up'),
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => popupsApi.publishPopup(id),
    onSuccess: (popup) => {
      invalidate(popup.id);
      toast.success(
        popup.status === 'scheduled'
          ? 'Scheduled — it will appear at its start time'
          : 'Published — it is live on your site',
      );
    },
    onError: (e: any) => toast.error(e.message || 'Could not publish the pop-up'),
  });

  const pauseMutation = useMutation({
    mutationFn: (id: string) => popupsApi.pausePopup(id),
    onSuccess: (popup) => { invalidate(popup.id); toast.success('Paused'); },
    onError: (e: any) => toast.error(e.message || 'Could not pause the pop-up'),
  });

  const duplicateMutation = useMutation({
    mutationFn: (id: string) => popupsApi.duplicatePopup(id),
    onSuccess: () => { invalidate(); toast.success('Duplicated as a draft'); },
    onError: (e: any) => toast.error(e.message || 'Could not duplicate the pop-up'),
  });

  return {
    popups: data?.data || [],
    total: data?.total || 0,
    page: data?.page || 1,
    perPage: data?.per_page || 20,
    totalPages: data?.total_pages || 0,
    isLoading,
    error,
    createPopup: createMutation.mutateAsync,
    updatePopup: (id: string, payload: UpdatePopupData) =>
      updateMutation.mutateAsync({ id, data: payload }),
    deletePopup: (id: string) => deleteMutation.mutate(id),
    publishPopup: (id: string) => publishMutation.mutate(id),
    pausePopup: (id: string) => pauseMutation.mutate(id),
    duplicatePopup: (id: string) => duplicateMutation.mutate(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
  };
};

export const usePopup = (id: string) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['popup', id],
    queryFn: () => popupsApi.getPopup(id),
    enabled: !!id,
  });
  return { popup: data, isLoading, error };
};

export const usePopupAnalytics = (id: string, days = 30) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['popup-analytics', id, days],
    queryFn: () => popupsApi.getAnalytics(id, days),
    enabled: !!id,
    staleTime: 60000,
  });
  return { analytics: data, isLoading, error };
};

export const usePopupTemplates = () =>
  useQuery({
    queryKey: ['popup-templates'],
    queryFn: popupsApi.getTemplates,
    staleTime: 5 * 60 * 1000,
  });
