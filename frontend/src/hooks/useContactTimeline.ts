import { useInfiniteQuery } from '@tanstack/react-query';
import { contactsApi } from '@/api/contacts';

const PAGE_SIZE = 20;

export const useContactTimeline = (contactId: string) => {
  const query = useInfiniteQuery({
    queryKey: ['contact-timeline', contactId],
    queryFn: ({ pageParam = 0 }) =>
      contactsApi.getContactTimeline(contactId, { limit: PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.results.length, 0);
      return loaded < lastPage.count ? loaded : undefined;
    },
    enabled: !!contactId,
    staleTime: 60000,
  });

  const events = query.data?.pages.flatMap((p) => p.results) ?? [];
  const total = query.data?.pages[0]?.count ?? 0;

  return {
    events,
    total,
    isLoading: query.isLoading,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
  };
};
