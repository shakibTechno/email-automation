import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  getLandingPageTemplates,
  getLandingPageTemplate,
  saveAsTemplate,
} from '@/api/landing-pages';
import type { TemplateCategory, SaveAsTemplateData } from '@/types/landing-page';

export const useLandingPageTemplates = (params?: {
  category?: TemplateCategory;
  is_system?: boolean;
  search?: string;
}) => {
  const query = useQuery({
    queryKey: ['landing-page-templates', params],
    queryFn: () => getLandingPageTemplates(params),
  });

  return {
    templates: query.data?.results ?? [],
    total: query.data?.count ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
};

export const useLandingPageTemplate = (id: string) => {
  const query = useQuery({
    queryKey: ['landing-page-template', id],
    queryFn: () => getLandingPageTemplate(id),
    enabled: !!id,
  });

  return {
    template: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
};

export const useSaveAsTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SaveAsTemplateData) => saveAsTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['landing-page-templates'] });
      toast.success('Template saved successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to save template');
    },
  });
};
