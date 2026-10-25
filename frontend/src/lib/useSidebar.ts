import { useCallback, useEffect, useState } from 'react';

const DEFAULT_STORAGE_KEY = 'mailflow-sidebar-collapsed';

/**
 * Two independent pieces of state, because the rail behaves differently at
 * each size:
 *   collapsed — desktop: the rail narrows to icons only. Remembered.
 *   open      — below lg: the rail slides in over the content. Never
 *               remembered, and always closed on navigation.
 *
 * `storageKey` is a parameter because more than one rail now uses this —
 * the tenant app and the landlord console. Sharing one key would make
 * collapsing one collapse the other, which reads as a bug.
 */
export const useSidebar = (storageKey: string = DEFAULT_STORAGE_KEY) => {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(storageKey) === '1';
    } catch {
      return false;
    }
  });
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, collapsed ? '1' : '0');
    } catch {
      /* private mode — the choice just will not persist */
    }
  }, [collapsed, storageKey]);

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
