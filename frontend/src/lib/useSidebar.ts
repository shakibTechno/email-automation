import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'mailflow-sidebar-collapsed';

/**
 * Two independent pieces of state, because the rail behaves differently at
 * each size:
 *   collapsed — desktop: the rail narrows to icons only. Remembered.
 *   open      — below lg: the rail slides in over the content. Never
 *               remembered, and always closed on navigation.
 */
export const useSidebar = () => {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === '1';
    } catch {
      return false;
    }
  });
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
    } catch {
      /* private mode — the choice just will not persist */
    }
  }, [collapsed]);

  // Escape closes the mobile drawer, which is otherwise a trap on a phone.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  return {
    collapsed,
    open,
    toggleCollapsed: useCallback(() => setCollapsed((c) => !c), []),
    toggleOpen: useCallback(() => setOpen((o) => !o), []),
    close: useCallback(() => setOpen(false), []),
  };
};
