import { PopupStatus, popupStatusLabels } from '@/types/popup';

const styles: Record<PopupStatus, string> = {
  draft: 'bg-secondary text-muted-foreground',
  scheduled: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
  published: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200',
  paused: 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
};

interface Props {
  status: PopupStatus;
  /** Published but outside its schedule window. Saying "Published" there is a
   *  lie the marketer then has to debug. */
  isLive?: boolean;
}

export const PopupStatusBadge = ({ status, isLive }: Props) => {
  const label =
    status === 'published' && isLive === false ? 'Ended' : popupStatusLabels[status];
  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {label}
    </span>
  );
};
