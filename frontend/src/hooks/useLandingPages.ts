import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  getLandingPages,
  getLandingPage,
  createLandingPage,
  updateLandingPage,
  deleteLandingPage,
  publishLandingPage,
  unpublishLandingPage,
  duplicateLandingPage,
  saveDesign,
  previewLandingPage,
} from '@/api/landing-pages';
import type {
  LandingPageFilters,
  CreateLandingPageData,
  UpdateLandingPageData,
  SaveDesignData,
} from '@/types/landing-page';

export const useLandingPages = (filters?: LandingPageFilters) => {
  const query = useQuery({
    queryKey: ['landing-pages', filters],
    queryFn: () => getLandingPages(filters),
  });

  return {
    landingPages: query.data?.results ?? [],
    total: query.data?.count ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
};

export const useLandingPage = (id: string) => {
  const query = useQuery({
    queryKey: ['landing-page', id],
    queryFn: () => getLandingPage(id),
    enabled: !!id,
  });

  return {
    landingPage: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
};

export const useCreateLandingPage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateLandingPageData) => createLandingPage(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
      toast.success('Landing page created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to create landing page');
    },
  });
};

export const useUpdateLandingPage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateLandingPageData }) =>
      updateLandingPage(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
      queryClient.invalidateQueries({ queryKey: ['landing-page', id] });
      toast.success('Landing page updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to update landing page');
    },
  });
};

export const useDeleteLandingPage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteLandingPage(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
      toast.success('Landing page deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to delete landing page');
    },
  });
};

export const usePublishLandingPage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => publishLandingPage(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
      queryClient.invalidateQueries({ queryKey: ['landing-page', id] });
      toast.success('Landing page published successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to publish landing page');
    },
  });
};

export const useUnpublishLandingPage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => unpublishLandingPage(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
      queryClient.invalidateQueries({ queryKey: ['landing-page', id] });
      toast.success('Landing page unpublished successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to unpublish landing page');
    },
  });
};

export const useDuplicateLandingPage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => duplicateLandingPage(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
      toast.success('Landing page duplicated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to duplicate landing page');
    },
  });
};

export const useSaveDesign = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: SaveDesignData }) =>
      saveDesign(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['landing-page', id] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to save design');
    },
  });
};

export const usePreviewLandingPage = (id: string) => {
  return useQuery({
    queryKey: ['landing-page-preview', id],
    queryFn: () => previewLandingPage(id),
    enabled: !!id,
  });
};
