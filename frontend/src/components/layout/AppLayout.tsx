import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useSidebar } from '@/lib/useSidebar';
import { cn } from '@/lib/utils';

/**
 * Fixed ribbon across the top, rail attached to the left edge beneath it, and
 * the content offset by both. The rail is `position: fixed`, so the offset has
 * to be a margin on the content rather than a flex sibling.
 */
export const AppLayout = () => {
  const { collapsed, open, toggleCollapsed, toggleOpen, close } = useSidebar();
  const { pathname } = useLocation();

  // A drawer left open across a route change hides the page the user asked for.
  useEffect(() => close(), [pathname, close]);

  return (
    <div className="app-ground min-h-screen">
      <Header
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
        onToggleDrawer={toggleOpen}
      />

      <Sidebar collapsed={collapsed} open={open} onNavigate={close} />

      {/* Scrim for the mobile drawer. Not rendered at all when inactive. */}
      {open && (
        <button
          type="button"
          onClick={close}
          aria-label="Close navigation"
          className="fixed inset-0 top-14 z-30 bg-foreground/30 lg:hidden"
        />
      )}

      <div
        className={cn(
          'pt-14 transition-[margin] duration-200',
          collapsed ? 'lg:ml-[68px]' : 'lg:ml-[238px]'
        )}
      >
        <main className="min-w-0 p-3.5">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
