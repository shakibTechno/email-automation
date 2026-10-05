import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { contactsApi } from '@/api/contacts';
import {
  ContactFilters,
  CreateContactData,
  UpdateContactData,
  BulkActionData,
} from '@/types/contact';
import { PaginationParams } from '@/types/api';

export const useContacts = (filters?: ContactFilters & PaginationParams) => {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['contacts', filters],
    queryFn: () => contactsApi.getContacts(filters),
    staleTime: 30000, // 30 seconds
  });

  const createMutation = useMutation({
    mutationFn: contactsApi.createContact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      toast.success('Contact created successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create contact');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateContactData }) =>
      contactsApi.updateContact(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['contact', variables.id] });
      toast.success('Contact updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update contact');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: contactsApi.deleteContact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      toast.success('Contact deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete contact');
    },
  });

  const bulkActionMutation = useMutation({
    mutationFn: contactsApi.bulkAction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      toast.success('Bulk action completed successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Bulk action failed');
    },
  });

  const exportMutation = useMutation({
    mutationFn: contactsApi.exportContacts,
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `contacts_${new Date().toISOString()}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('Contacts exported successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to export contacts');
    },
  });

  const importMutation = useMutation({
    mutationFn: contactsApi.importContacts,
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      const r = response.results;
      toast.success(`Imported ${r.imported}, updated ${r.updated}, skipped ${r.skipped}.`);
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to import contacts');
    },
  });

  return {
    contacts: data?.data || [],
    total: data?.total || 0,
    page: data?.page || 1,
    perPage: data?.per_page || 20,
    totalPages: data?.total_pages || 0,
    isLoading,
    error,
    createContact: (data: CreateContactData) => createMutation.mutate(data),
    updateContact: (id: string, data: UpdateContactData) =>
      updateMutation.mutate({ id, data }),
    deleteContact: (id: string) => deleteMutation.mutate(id),
    bulkAction: (data: BulkActionData) => bulkActionMutation.mutate(data),
    exportContacts: (filters?: ContactFilters) => exportMutation.mutate(filters),
    importContacts: (formData: FormData) => importMutation.mutate(formData),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isExporting: exportMutation.isPending,
    isImporting: importMutation.isPending,
  };
};

export const useDuplicateContacts = () => {
  return useQuery({
    queryKey: ['contacts', 'duplicates'],
    queryFn: contactsApi.getDuplicates,
    staleTime: 60000,
  });
};

export const useMergeContacts = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contactsApi.mergeContacts,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      toast.success('Contacts merged successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to merge contacts');
    },
  });
};

export const useContact = (id: string) => {
  const { data: contact, isLoading, error } = useQuery({
    queryKey: ['contact', id],
    queryFn: () => contactsApi.getContact(id),
    enabled: !!id,
  });

  return {
    contact,
    isLoading,
    error,
  };
};
